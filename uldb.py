import sys
from database import Database, FieldType


# I used AI assistance in the development of this code. Specifically, I used
# claude.ai to help with the following methods: _parse_value, from_update_where,
# from_if_get(),from_delete_where()
#The core logic and the approach was developed by me, and the AI helped with the .


class ULDB:
    """Command-line interpreter for managing ULDB databases."""

    def __init__(self):
        """Initialize the ULDB interpreter with no open database."""
        self.db = None
        self.db_name = None

    def _split_args(self, args_str: str) -> list:
        """
        Splits a comma-separated argument string, respecting quoted substrings.

        Args:
            args_str (str): The raw argument string.

        Returns:
            list: List of individual arguments.
        """
        parts = []
        current = ""
        in_quotes = False
        for char in args_str:
            if char == '"' and not in_quotes:
                in_quotes = True
                current += char
            elif char == '"' and in_quotes:
                in_quotes = False
                current += char
            elif char == ',' and not in_quotes:
                parts.append(current.strip())
                current = ""
            else:
                current += char
        if current.strip():
            parts.append(current.strip())
        return parts

    def open_db(self, name: str):
        """
        Opens or creates a database with the given name.

        Args:
            name (str): Name of the database file.
        """
        if self.db is not None:
            print(f"Error: A database is already open ({self.db_name})")
            return
        try:
            self.db = Database(name)
            self.db_name = name
        except Exception as e:
            print(f"Error: Cannot open database '{name}' ({e})")

    def create_table(self, args: str):
        """
        Creates a table with specified fields and types.

        Syntax:
            create_table(table_name, field1=TYPE, field2=TYPE, ...)

        Args:
            args (str): Comma-separated arguments.
        """
        if self.db is None:
            print("Error: No database open")
            return

        parts = self._split_args(args)
        if len(parts) < 2:
            print("Error: Syntax error in create_table")
            return

        table_name = parts[0]
        field_parts = parts[1:]
        fields = []
        names_seen = set()

        for fp in field_parts:
            if '=' not in fp:
                print("Error: Syntax error in create_table")
                return
            name, type_str = fp.split('=', 1)
            name = name.strip()
            type_str = type_str.strip()

            if not name or not type_str:
                print("Error: Syntax error in create_table")
                return
            if name in names_seen:
                print(f"Error: Duplicate field name '{name}' in table definition")
                return
            names_seen.add(name)

            if type_str not in ("INTEGER", "STRING"):
                print(f"Error: Unknown field type '{type_str}'")
                return

            field_type = FieldType.INTEGER if type_str == "INTEGER" else FieldType.STRING
            fields.append((name, field_type))

        try:
            self.db.create_table(table_name, *fields)
        except ValueError as e:
            print(f"Error: {e}")

    def delete_table(self, table_name: str):
        """
        Deletes a table from the database.

        Args:
            table_name (str): Name of the table to delete.
        """
        if self.db is None:
            print("Error: No database open")
            return
        try:
            self.db.delete_table(table_name)
        except ValueError as e:
            print(f"Error: {e}")

    def list_tables(self):
        """
        Lists all tables in the currently opened database.
        """
        if self.db is None:
            print("Error: No database open")
            return
        tables = self.db.list_tables()
        for name in tables:
            print(name)

    def insert_to(self, args: str):
        """
        Inserts a record into a table.

        Syntax:
            insert_to(table_name, field1=value, field2=value, ...)

        Args:
            args (str): Comma-separated arguments.
        """
        if self.db is None:
            print("Error: No database open")
            return

        parts = self._split_args(args)
        if len(parts) < 2:
            print("Error: Syntax error in insert_to")
            return

        table_name = parts[0]
        field_assignments = parts[1:]
        entry_data = {}

        for assign in field_assignments:
            if '=' not in assign:
                print("Error: Syntax error in insert_to")
                return
            fname, fval = assign.split('=', 1)
            fname = fname.strip()
            fval = fval.strip()

            if not fname:
                print("Error: Syntax error in insert_to")
                return

            if len(fval) >= 2 and fval[0] == '"' and fval[-1] == '"':
                entry_data[fname] = fval[1:-1]
            else:
                if fval.isdigit() or (fval.startswith('-') and fval[1:].isdigit()):
                    try:
                        entry_data[fname] = int(fval)
                    except Exception:
                        print(f"Error: Invalid integer value '{fval}'")
                        return
                else:
                    print(f"Error: Invalid value syntax for '{fname}'")
                    return

        try:
            self.db.add_entry(table_name, entry_data)
        except ValueError as e:
            print(f"Error: {e}")

    def from_if_get(self, args: str):
        """
        Retrieves records matching a condition from a table.

        Syntax:
            from_if_get(table_name, cond_field=cond_value, field1, field2, ...)

        Args:
            args (str): Comma-separated arguments.
        """
        if self.db is None:
            print("Error: No database open")
            return

        parts = self._split_args(args)
        if len(parts) < 3:
            print("Error: Syntax error in from_if_get")
            return

        table_name = parts[0]
        cond_part = parts[1]
        fields_requested = parts[2:]

        if '=' not in cond_part:
            print("Error: Syntax error in from_if_get")
            return

        cond_name, cond_val_str = cond_part.split('=', 1)
        cond_name = cond_name.strip()
        cond_val_str = cond_val_str.strip()

        if len(cond_val_str) >= 2 and cond_val_str[0] == '"' and cond_val_str[-1] == '"':
            cond_value = cond_val_str[1:-1]
        elif cond_val_str.isdigit() or (cond_val_str.startswith('-') and cond_val_str[1:].isdigit()):
            cond_value = int(cond_val_str)
        else:
            print(f"Error: Invalid condition value '{cond_val_str}'")
            return

        if len(fields_requested) == 1 and fields_requested[0] == "*":
            try:
                signature = self.db.get_table_signature(table_name)
                fields = tuple(name for name, _ in signature)
                entries = self.db.get_entries(table_name, cond_name, cond_value)
                for entry in entries:
                    result = tuple(entry[field] for field in fields)
                    print(result)
            except ValueError as e:
                print(f"Error: {e}")
            return

        try:
            fields = tuple(field.strip() for field in fields_requested)
            entries = self.db.get_entries(table_name, cond_name, cond_value)

            if len(fields) == 1:
                field = fields[0]
                for entry in entries:
                    value = entry.get(field)
                    if field == "id" and isinstance(value, int):
                        value += 1
                    print(value)
            else:
                for entry in entries:
                    result = tuple(
                        (entry[field] + 1 if field == "id" and isinstance(entry[field], int)
                         else entry[field])
                        for field in fields
                    )
                    print(result)
        except ValueError as e:
            print(f"Error: {e}")

    def from_delete_where(self, args: str):
        """
        Deletes records matching a condition from a table.

        Syntax:
            from_delete_where(table_name, cond_field=cond_value)

        Args:
            args (str): Comma-separated arguments.
        """
        if self.db is None:
            print("Error: No database open")
            return

        parts = self._split_args(args)
        if len(parts) != 2:
            print("Error: Syntax error in from_delete_where")
            return

        table_name = parts[0]
        cond_part = parts[1]

        if '=' not in cond_part:
            print("Error: Syntax error in from_delete_where")
            return

        cond_name, cond_val_str = cond_part.split('=', 1)
        cond_name = cond_name.strip()
        cond_val_str = cond_val_str.strip()

        if len(cond_val_str) >= 2 and cond_val_str[0] == '"' and cond_val_str[-1] == '"':
            cond_value = cond_val_str[1:-1]
        elif cond_val_str.isdigit() or (cond_val_str.startswith('-') and cond_val_str[1:].isdigit()):
            cond_value = int(cond_val_str)
        else:
            print(f"Error: Invalid condition value '{cond_val_str}'")
            return

        try:
            self.db.delete_entries(table_name, cond_name, cond_value)
        except ValueError as e:
            print(f"Error: {e}")

    def _parse_value(self, val_str: str):
        """
        Parses a string into an int or str, depending on format.

        Args:
            val_str (str): The raw value string.

        Returns:
            int or str or None
        """
        if len(val_str) >= 2 and val_str[0] == '"' and val_str[-1] == '"':
            return val_str[1:-1]
        elif val_str.isdigit() or (val_str.startswith('-') and val_str[1:].isdigit()):
            try:
                return int(val_str)
            except Exception:
                print(f"Error: Invalid integer value '{val_str}'")
                return None
        else:
            print(f"Error: Invalid value syntax '{val_str}'")
            return None

    def from_update_where(self, args: str):
        """
        Updates records in a table that match a given condition.

        Syntax:
            from_update_where(table_name, cond_field=cond_value, target_field=new_value)

        Args:
            args (str): Comma-separated arguments.
        """
        if self.db is None:
            print("Error: No database open")
            return

        parts = self._split_args(args)
        if len(parts) != 3:
            print("Error: Syntax error in from_update_where")
            return

        table_name = parts[0]
        cond_part = parts[1]
        update_part = parts[2]

        if '=' not in cond_part or '=' not in update_part:
            print("Error: Syntax error in from_update_where")
            return

        cond_name, cond_val_str = cond_part.split('=', 1)
        update_name, new_val_str = update_part.split('=', 1)

        cond_name = cond_name.strip()
        cond_val_str = cond_val_str.strip()
        update_name = update_name.strip()
        new_val_str = new_val_str.strip()

        cond_value = self._parse_value(cond_val_str)
        new_value = self._parse_value(new_val_str)

        if cond_value is None or new_value is None:
            return

        if cond_name == "id" and isinstance(cond_value, int):
            cond_value -= 1
        if update_name == "id" and isinstance(new_value, int):
            new_value -= 1

        try:
            self.db.update_entries(
                table_name, cond_name, cond_value, update_name, new_value
            )
        except ValueError as e:
            print(f"Error: {e}")

    def process_command(self, command: str):
        """
        Parses and executes a single command from user input.

        Args:
            command (str): Raw command string.
        """
        command = command.strip()
        if command == "":
            return
        if command.lower() in ("quit", "q"):
            raise SystemExit

        if "(" in command and command.endswith(")"):
            name, rest = command.split("(", 1)
            name = name.strip()
            args = rest[:-1]
        else:
            print("Error: Invalid command syntax")
            return

        if name == "open":
            self.open_db(args)
        elif name == "create_table":
            self.create_table(args)
        elif name == "delete_table":
            self.delete_table(args)
        elif name == "list_tables":
            if args.strip():
                print("Error: list_tables() takes no arguments")
            else:
                self.list_tables()
        elif name == "insert_to":
            self.insert_to(args)
        elif name == "from_if_get":
            self.from_if_get(args)
        elif name == "from_delete_where":
            self.from_delete_where(args)
        elif name == "from_update_where":
            self.from_update_where(args)
        else:
            print(f"Error: Unknown command '{name}'")


def main():
    """Entry point for the ULDB command-line interface."""
    interpreter = ULDB()

    if len(sys.argv) > 1:
        filename = sys.argv[1]
        try:
            with open(filename, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.rstrip("\n")
                    if not line:
                        continue
                    interpreter.process_command(line)
        except FileNotFoundError:
            print(f"Error: Script file '{filename}' not found")
        except SystemExit:
            return
    else:
        try:
            while True:
                sys.stdout.write("uldb:: ")
                sys.stdout.flush()
                user_input = sys.stdin.readline()
                if user_input == "":
                    break
                interpreter.process_command(user_input)
        except SystemExit:
            pass


if __name__ == "__main__":
    main()
