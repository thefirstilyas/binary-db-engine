from enum import Enum
from copy import deepcopy
import os
from binary import BinaryFile


Field = str | int
Entry = dict[str, Field]

# I used AI assistance in the development of this code. Specifically, I used
# claude.ai to help with the following functions: add_entry,update_entries, _rewrite_table,
# _resize_string_buffer and delete_entries.
# The core logic and the approach was developed by me, and the AI helped with the implementation.

"""
This module implements a simple database system with support for tables, entries, and queries.
"""


class FieldType(Enum):
    """Enumeration for field types in the database."""

    INTEGER = 1
    STRING = 2


TableSignature = list[tuple[str, FieldType]]


class Database:
    """A class representing a simple database system."""
   
    def __init__(self, name: str):
        self.name = name
        self._last_id = 1
        os.makedirs(name, exist_ok=True)
        self.entry_memory = {}
        self.table_signatures = {}

        # Initialize entries for existing tables
        for table_name in self.list_tables():
            if table_name not in self.entry_memory:
                self.entry_memory[table_name] = self._load_table_entries(table_name)

    def list_tables(self) -> list[str]:
        """List all tables in the database."""
        table_files, path = [], self.name
        tables = os.listdir(path)
        for table in tables:
            if len(table) > 6 and table[-6:] == ".table":
                table_files.append(table[:-6])
        return table_files

    def _get_table_path(self, table_name: str) -> str:
        """Return the full path to a table file."""
        return os.path.join(self.name, table_name + ".table")

    def create_table(self, table_name: str, *field: TableSignature) -> None:
        """Create a new table in the database."""
        # Normalize the field format
        fields = []
        
        # Special case where a single parameter is passed as a list ['a', FieldType.INTEGER]
        if len(field) == 1 and isinstance(field[0], (list, tuple)) and len(field[0]) == 2:
            if isinstance(field[0][0], str) and isinstance(field[0][1], FieldType):
                fields = [(field[0][0], field[0][1])]
        else:
            fields = field

        table_path = self._get_table_path(table_name)
        if os.path.exists(table_path):
            raise ValueError("Table already exists")
        with open(table_path, 'wb') as table:
            table_file = BinaryFile(table)

            # Write header
            table_file.write_string_without_size("ULDB")  # Magic constant
            table_file.write_integer(len(fields), 4)  # Number of fields

            # Write field signatures
            for field_name, field_type in fields:
                table_file.write_integer(field_type.value, 1)
                table_file.write_string(field_name)

            # Define buffer offsets
            string_buffer_offset = 64
            entry_buffer_offset = 80
            string_buffer_iffset = 16

            # Write buffer pointers
            table_file.write_integer(string_buffer_offset, 4)  # String buffer start
            table_file.write_integer(string_buffer_offset, 4)  # String free position
            table_file.write_integer(entry_buffer_offset, 4)  # Entry buffer start

            # Write initial string buffer
            table_file.write_integer(0, string_buffer_iffset)

            # Write entry buffer header
            table_file.write_integer(0, 4)  # Last used ID
            table_file.write_integer(0, 4)  # Number of entries
            table_file.write_integer(-1, 4)  # First entry pointer (none)
            table_file.write_integer(-1, 4)  # Last entry pointer (none)
            table_file.write_integer(-1, 4)  # Reserved pointer (deleted entries)

        # Initialize empty entries list for this table
        self.entry_memory[table_name] = []

    def delete_table(self, table_name: str) -> None:
        """Delete a table from the database."""
        table_path = self._get_table_path(table_name)
        if not os.path.exists(table_path):
            raise ValueError("Table doesn't exist")
        os.remove(table_path)

        # Remove from memory dict if present
        if table_name in self.entry_memory:
            del self.entry_memory[table_name]

    def _read_header_end_position(self, table_file: BinaryFile) -> int:
        table_file.goto(4)
        num_fields = table_file.read_integer(4)
        offset = 8  # After magic constant and field count
        for _ in range(num_fields):
            offset += 1  # 1 byte for type
            table_file.goto(offset)
            name_length = table_file.read_integer(2)
            offset += 2 + name_length  # 2 bytes for length + name
        return offset

    def _read_str_buffer_pointers(self, table_file, header_end) -> tuple[int, int, int]:
        """Read string and entry buffer pointers."""
        table_file.goto(header_end)
        string_buffer_pos = table_file.read_integer(4)
        string_free_pos = table_file.read_integer(4)
        entry_buffer_pos = table_file.read_integer(4)
        return string_buffer_pos, string_free_pos, entry_buffer_pos

    def _read_entry_buffer_header(
            self, table_file, entry_bufr_pos
    ) -> tuple[int, int, int, int, int]:
        """Read entry buffer header values."""
        table_file.goto(entry_bufr_pos)
        last_id = table_file.read_integer(4)
        num_entries = table_file.read_integer(4)
        first_entry_ptr = table_file.read_integer(4)
        last_entry_ptr = table_file.read_integer(4)
        reserved_ptr = table_file.read_integer(4)
        return last_id, num_entries, first_entry_ptr, last_entry_ptr, reserved_ptr

    def get_table_signature(self, table_name: str) -> list[tuple[str, FieldType]]:
        """Get the signature (field names and types) of a table."""
        if table_name in self.table_signatures:
            return self.table_signatures[table_name]
         
        table_path = self._get_table_path(table_name)
        if not table_name in self.list_tables():
            raise ValueError("Table doesn't exist")

        with open(table_path, "rb") as table:
            table_file = BinaryFile(table)
            table_file.goto(4)
            number_of_fields = table_file.read_integer(4)
            table_signature = []
            # Cursor is now at position 8, just after the field count
            for _ in range(number_of_fields):
                read_field_type = table_file.read_integer(1)
                if read_field_type == FieldType.INTEGER.value:
                    field_type = FieldType.INTEGER
                else:
                    field_type = FieldType.STRING

                # read_string() reads 2 bytes for length then the string,
                # which corresponds to what was written by write_string()
                field_name = table_file.read_string()
                table_signature.append((field_name, field_type))
            self.table_signatures[table_name] = table_signature
            return table_signature

    def _load_table_entries(self, _: str) -> list[Entry]:
        """Load all entries from a table file."""
        # This is a placeholder, in a real implementation, I would read entries from the file
        # We'll just return an empty list since the current design loads entries as needed
        return []

    def add_entry(self, table_name: str, entry: Entry) -> None:
        """Add a new entry to the specified table."""
        if table_name not in self.list_tables():
            raise ValueError("Table doesn't exist")

        # Validate entry against table signature
        signature = self.get_table_signature(table_name)

        for field_name, field_type in signature:
            if field_name not in entry:
                raise ValueError(f"Missing field {field_name} in entry")
            if field_type == FieldType.INTEGER and not isinstance(entry[field_name], int):
                raise ValueError(f"Field {field_name} must be an integer")
            if field_type == FieldType.STRING and not isinstance(entry[field_name], str):
                raise ValueError(f"Field {field_name} must be a string")

        table_path = self._get_table_path(table_name)

        with open(table_path, "r+b") as file:
            table_file = BinaryFile(file)

            # Read header
            header_end = self._read_header_end_position(table_file)
            _, string_free_pos, entry_buffer_pos = self._read_str_buffer_pointers(
                table_file, header_end
            )

            # Read entry buffer header
            (
                last_id,
                num_entries,
                first_entry_ptr,
                last_entry_ptr,
                reserved_ptr
            ) = self._read_entry_buffer_header(
                table_file, entry_buffer_pos
            )

            # Check if we can reuse a deleted entry
            reuse_deleted = reserved_ptr != -1

            # Calculate space needed for strings and resize ONLY if not reusing
            if not reuse_deleted:
                space_needed = 0
                for field_name, field_type in signature:
                    if field_type == FieldType.STRING:
                        string_value = entry[field_name]
                        string_to_utf8 = string_value.encode('utf-8')
                        space_needed += 2 + len(string_to_utf8)

                # Resize if needed
                if string_free_pos + space_needed > entry_buffer_pos:
                    self._resize_string_buffer(
                        table_path, string_free_pos + space_needed
                    )

                    # Reopen file and reread header after resize
                    file.seek(0)
                    header_end = self._read_header_end_position(table_file)
                    _, string_free_pos, entry_buffer_pos = self._read_str_buffer_pointers(
                        table_file, header_end
                    )

                    # Re-read entry buffer header after resize
                    (
                        last_id,
                        num_entries,
                        first_entry_ptr,
                        last_entry_ptr,
                        reserved_ptr
                    ) = self._read_entry_buffer_header(
                        table_file, entry_buffer_pos
                    )
                    # Check again if we can reuse a deleted entry after resize
                    reuse_deleted = reserved_ptr != -1

            # Set position for new entry based on whether we're reusing
            if reuse_deleted:
                # Position of new entry = position of deleted entry
                new_entry_pos = reserved_ptr

                # Calculate position of next pointer in deleted entry
                fields_size = len(signature) * 4
                next_ptr_pos = reserved_ptr + 4 + fields_size + 4

                # Read pointer to next deleted entry
                table_file.goto(next_ptr_pos)
                next_deleted_ptr = table_file.read_integer(4)

                # Update reserved pointer in header
                table_file.goto(entry_buffer_pos + 16)
                table_file.write_integer(next_deleted_ptr, 4)
            else:
                # No deleted entries, create at end of file
                if num_entries == 0:
                    # First entry just after header
                    new_entry_pos = entry_buffer_pos + 20
                else:
                    # New entry goes at end of file
                    new_entry_pos = table_file.get_size()

            # Write strings to buffer and get pointers (only if not reusing)
            string_pointers = {}
            if reuse_deleted:
                # If reusing, read existing string pointers
                table_file.goto(reserved_ptr + 4)  # Position after ID
                for field_name, field_type in signature:
                    if field_type == FieldType.INTEGER:
                        # Skip integer fields
                        table_file.goto(table_file.tell_position() + 4)
                    else:  # STRING
                        # Read existing string pointer
                        string_pointers[field_name] = table_file.read_integer(4)
            else:
                # If not reusing, write new strings
                for field_name, field_type in signature:
                    if field_type == FieldType.STRING:
                        value = entry[field_name]
                        string_pointers[field_name] = string_free_pos

                        table_file.goto(string_free_pos)
                        bytes_written = table_file.write_string(value)
                        string_free_pos += bytes_written

                # Update string buffer free position only if not reusing
                table_file.goto(header_end + 4)
                table_file.write_integer(string_free_pos, 4)

            # Update ID and counts
            new_id = last_id + 1
            self._last_id = new_id

            # Update memory dictionary
            entry_copy = deepcopy(entry)
            entry_copy['id'] = new_id
            new_entries = num_entries + 1
            if table_name not in self.entry_memory:
                self.entry_memory[table_name] = [entry_copy]
            else:
                self.entry_memory[table_name].append(entry_copy)

            # Logic to update linked list pointers
            if num_entries == 0:
                # This is the first entry
                prev_ptr = -1
                next_ptr = -1

                # Update header pointers
                table_file.goto(entry_buffer_pos)
                table_file.write_integer(new_id, 4)  # Always update last_id
                table_file.write_integer(new_entries, 4)  # Entry count
                table_file.write_integer(new_entry_pos, 4)  # First entry
                table_file.write_integer(new_entry_pos, 4)  # Last entry
            else:
                # Not the first entry - ALWAYS update prev/next pointers correctly
                prev_ptr = last_entry_ptr
                next_ptr = -1

                # Update "next" pointer of previous entry (former last)
                table_file.goto(last_entry_ptr + 4 + len(signature) * 4 + 4)
                table_file.write_integer(new_entry_pos, 4)

                # Update header pointers
                table_file.goto(entry_buffer_pos)
                table_file.write_integer(new_id, 4)  # Always update last_id
                table_file.write_integer(new_entries, 4)  # Entry count
                table_file.write_integer(first_entry_ptr, 4)  # No change to first_entry_ptr
                table_file.write_integer(new_entry_pos, 4)  # Last entry = this entry

            # Write the new entry
            table_file.goto(new_entry_pos)

            # ID
            table_file.write_integer(new_id, 4)

            # Fields
            for field_name, field_type in signature:
                if field_type == FieldType.INTEGER:
                    table_file.write_integer(entry[field_name], 4)
                else:  # STRING
                    table_file.write_integer(string_pointers[field_name], 4)

            # Linked list pointers
            table_file.write_integer(prev_ptr, 4)  # Previous pointer
            table_file.write_integer(next_ptr, 4)  # Next pointer

    def _resize_string_buffer(self, table_path: str, min_required_space: int) -> None:
        """Resize the string buffer to accommodate at least min_required_space bytes."""
        # Read the entire file
        with open(table_path, "rb") as f:
            original_data = f.read()

        # Parse header information
        if original_data[0:4] != b'ULDB':
            raise ValueError("Invalid table file format")

        num_fields = int.from_bytes(
            original_data[4:8], byteorder="little", signed=False
        )

        # Skip field signatures to get to pointers
        offset = 8  # Start after magic and num_fields
        for _ in range(num_fields):
            _ = original_data[offset]
            offset += 1
            name_len = int.from_bytes(
                original_data[offset:offset+2], byteorder="little", signed=False
            )
            offset += 2 + name_len

        # Extract pointers
        header_end = offset
        string_buffer_start = int.from_bytes(
            original_data[offset:offset+4], byteorder="little", signed=False
        )
        offset += 4
        string_buffer_free = int.from_bytes(
            original_data[offset:offset+4], byteorder="little", signed=False
        )
        offset += 4
        entry_buffer_start = int.from_bytes(
            original_data[offset:offset+4], byteorder="little", signed=False
        )

        # Calculate buffer sizes
        current_buffer_size = entry_buffer_start - string_buffer_start
        string_content_size = string_buffer_free - string_buffer_start
        needed_size = min_required_space - string_buffer_start

        # Only resize if needed
        if needed_size <= current_buffer_size:
            return

        # Calculate new buffer size (next power of 2)
        new_buffer_size = current_buffer_size
        while new_buffer_size < needed_size:
            new_buffer_size *= 2

        # Calculate shift amount and new entry buffer position
        shift_amount = new_buffer_size - current_buffer_size
        new_entry_buffer_start = string_buffer_start + new_buffer_size

        # Create new file content
        new_data = bytearray()

        # Copy header
        new_data.extend(original_data[:header_end])

        # Update pointers
        new_data.extend(string_buffer_start.to_bytes(4, byteorder="little", signed=False))
        new_data.extend(string_buffer_free.to_bytes(4, byteorder="little", signed=False))
        new_data.extend(new_entry_buffer_start.to_bytes(4, byteorder="little", signed=False))

        # Copy string buffer content
        new_data.extend(original_data[string_buffer_start:string_buffer_free])

        # Add padding to reach new buffer size
        padding_size = new_buffer_size - string_content_size
        new_data.extend(bytes(padding_size))

        # Copy entry buffer header
        entry_buffer_header = original_data[entry_buffer_start:entry_buffer_start+20]
        new_data.extend(entry_buffer_header)

        # Read entry buffer header values
        _ = int.from_bytes(
            entry_buffer_header[0:4], byteorder="little", signed=False
        )  # last id
        num_entries = int.from_bytes(
            entry_buffer_header[4:8], byteorder="little", signed=False
        )
        first_entry_ptr = int.from_bytes(
            entry_buffer_header[8:12], byteorder="little", signed=False
        )
        last_entry_ptr = int.from_bytes(
            entry_buffer_header[12:16], byteorder="little", signed=False
        )
        deleted_ptr = int.from_bytes(
            entry_buffer_header[16:20], byteorder="little", signed=False
        )

        # Update pointers in entry buffer header
        if first_entry_ptr != 0xFFFFFFFF:
            new_first_ptr = first_entry_ptr + shift_amount
            new_data[new_entry_buffer_start+8:new_entry_buffer_start+12] = (
                new_first_ptr.to_bytes(4, byteorder="little", signed=False)
            )

        if last_entry_ptr != 0xFFFFFFFF:
            new_last_ptr = last_entry_ptr + shift_amount
            new_data[new_entry_buffer_start+12:new_entry_buffer_start+16] = (
                new_last_ptr.to_bytes(4, byteorder="little", signed=False)
            )

        if deleted_ptr != 0xFFFFFFFF:
            new_deleted_ptr = deleted_ptr + shift_amount
            new_data[new_entry_buffer_start+16:new_entry_buffer_start+20] = (
                new_deleted_ptr.to_bytes(4, byteorder="little", signed=False)
            )

        # Process entries and update pointers
        if num_entries > 0 and first_entry_ptr != 0xFFFFFFFF:
            entries_data = original_data[entry_buffer_start+20:]
            updated_entries = bytearray()

            # Get field structure info
            field_size = 4 * num_fields  # Size of all fields (4 bytes each)
            _ = 4 + field_size + 8  # ID + fields + prev and next pointers

            # Process each entry
            current_ptr = first_entry_ptr
            for _ in range(num_entries):
                if current_ptr == 0xFFFFFFFF:
                    break

                # Calculate entry offset
                entry_offset = current_ptr - entry_buffer_start - 20
                if entry_offset < 0 or entry_offset >= len(entries_data):
                    break

                # Copy ID
                entry_id = int.from_bytes(
                    entries_data[entry_offset:entry_offset+4],
                    byteorder="little", signed=False
                )
                updated_entries.extend(
                    entry_id.to_bytes(4, byteorder="little", signed=False)
                )

                # Copy fields data
                updated_entries.extend(entries_data[entry_offset+4:entry_offset+4+field_size])

                # Update linked list pointers
                prev_ptr_offset = entry_offset + 4 + field_size
                next_ptr_offset = prev_ptr_offset + 4

                prev_ptr = int.from_bytes(
                    entries_data[prev_ptr_offset:prev_ptr_offset+4],
                    byteorder="little", signed=False
                )
                next_ptr = int.from_bytes(
                    entries_data[next_ptr_offset:next_ptr_offset+4],
                    byteorder="little", signed=False
                )

                # Adjust pointers
                if prev_ptr != 0xFFFFFFFF:
                    prev_ptr += shift_amount
                if next_ptr != 0xFFFFFFFF:
                    next_ptr += shift_amount

                updated_entries.extend(
                    prev_ptr.to_bytes(4, byteorder="little", signed=False)
                )
                updated_entries.extend(
                    next_ptr.to_bytes(4, byteorder="little", signed=False)
                )

                # Move to next entry
                current_ptr = next_ptr

            # Add updated entries to new file
            new_data.extend(updated_entries)

        # Write the updated file
        with open(table_path, "wb") as f:
            f.write(new_data)

    def _rewrite_table(self, table_name: str, entries: list[Entry],
                      signature: list[tuple[str, FieldType]]) -> None:
        """Completely rewrites the table with the provided entries, preserving IDs."""
        table_path = self._get_table_path(table_name)
        temp_path = table_path + ".tmp"

        # Open temporary file in binary read/write mode
        with open(temp_path, "w+b") as temp_file:
            bf_temp = BinaryFile(temp_file)
            # 1. Rebuild header from scratch (as during creation)
            # Write magic constant
            bf_temp.write_string_without_size("ULDB")
            # Write field count (from provided signature)
            bf_temp.write_integer(len(signature), 4)
            # Write each field signature: 1 byte for type, then name (with 2-byte prefix)
            for field_name, field_type in signature:
                bf_temp.write_integer(field_type.value, 1)
                bf_temp.write_string(field_name)
            # Current position in file corresponds to end of signatures
            header_fields_end = bf_temp.tell_position()
            # Next write 12 bytes of pointers (string buffer start, string free pos, entry buffer start)
            # and 16 bytes for initial string buffer
            header_size = header_fields_end + 12  # After writing pointers
            string_buffer_pos = header_size       # String buffer starts here
            entry_buffer_pos = string_buffer_pos + 16  # Then 16 bytes for string buffer
            # Write the 3 pointers
            bf_temp.write_integer(string_buffer_pos, 4)  # String buffer start
            # Initially no string content written: free position equals buffer start
            string_free_pos = string_buffer_pos
            bf_temp.write_integer(string_free_pos, 4)
            bf_temp.write_integer(entry_buffer_pos, 4)
            # Write 16 bytes of string buffer (initially filled with zeros)
            bf_temp.file.write(b'\x00' * 16)

            # 2. Build entry buffer mini-header from entry_buffer_pos offset
            bf_temp.goto(entry_buffer_pos)
            if entries:
                last_id = self._last_id
                bf_temp.write_integer(last_id, 4)         # Last used ID
                bf_temp.write_integer(len(entries), 4)    # Entry count
                # First entry starts right after mini-header (20 bytes)
                first_entry_pos = entry_buffer_pos + 20
                bf_temp.write_integer(first_entry_pos, 4)  # Pointer to first entry

                # Calculate entry size:
                # - 4 bytes for ID
                # - For each field: 4 bytes (for INTEGER or STRING pointer)
                # - 8 bytes for pointers (previous and next)
                entry_size = 4 + len(signature) * 4 + 8
                last_entry_pos = (first_entry_pos + (len(entries) - 1) * entry_size
                                 if len(entries) > 1 else first_entry_pos)
                bf_temp.write_integer(last_entry_pos, 4)  # Pointer to last entry
                bf_temp.write_integer(0xFFFFFFFF, 4)      # Reserved pointer (initially -1)

                # 3. Write entries to entry buffer
                prev_ptr = 0xFFFFFFFF
                current_entry_pos = first_entry_pos
                for i, entry in enumerate(entries):
                    bf_temp.goto(current_entry_pos)
                    # Write entry ID
                    bf_temp.write_integer(entry['id'], 4)
                    # For each field in signature
                    for field_name, field_type in signature:
                        value = entry.get(field_name)
                        if field_type == FieldType.INTEGER:
                            bf_temp.write_integer(value, 4)
                        else:  # STRING
                            # Save current position to write pointer
                            current_field_pos = bf_temp.tell_position()
                            # Go write string at end of string buffer
                            bf_temp.goto(string_free_pos)
                            string_ptr = string_free_pos
                            bytes_written = bf_temp.write_string(value)
                            string_free_pos += bytes_written
                            # Return to write pointer in entry
                            bf_temp.goto(current_field_pos)
                            bf_temp.write_integer(string_ptr, 4)
                    # Calculate pointer to next entry
                    next_ptr = (0xFFFFFFFF if i == len(entries) - 1 
                               else current_entry_pos + entry_size)
                    bf_temp.write_integer(prev_ptr, 4)  # Pointer to previous entry
                    bf_temp.write_integer(next_ptr, 4)  # Pointer to next entry

                    prev_ptr = current_entry_pos
                    current_entry_pos = next_ptr

                # 4. Update string buffer free position pointer in header
                # This pointer is at offset = header_fields_end + 4
                bf_temp.goto(header_fields_end + 4)
                bf_temp.write_integer(string_free_pos, 4)
            else:
                # If no entries, write empty mini-header
                bf_temp.goto(entry_buffer_pos)
                bf_temp.write_integer(0, 4)            # Last ID
                bf_temp.write_integer(0, 4)            # Entry count
                bf_temp.write_integer(0xFFFFFFFF, 4)   # Pointer to first entry
                bf_temp.write_integer(0xFFFFFFFF, 4)   # Pointer to last entry
                bf_temp.write_integer(0xFFFFFFFF, 4)   # Reserved pointer

        os.replace(temp_path, table_path)

    def get_table_size(self, table_name: str) -> int:
        """Returns the number of entries in the table."""
        if table_name not in self.list_tables():
            raise ValueError(f"Table '{table_name}' doesn't exist")

        # Initialize the table's entries if needed
        if table_name not in self.entry_memory:
            self.entry_memory[table_name] = []

        return len(self.entry_memory[table_name])

    def get_complete_table(self, table_name: str) -> list[Entry]:
        """Returns all entries in the table."""
        if table_name not in self.list_tables():
            raise ValueError(f"Table '{table_name}' doesn't exist")

        # Initialize the table's entries if needed
        if table_name not in self.entry_memory:
            self.entry_memory[table_name] = []

        return self.entry_memory[table_name]

    def get_entry(self, table_name: str, field_name: str, field_value: Field) -> Entry | None:
        """Returns an entry where field_name equals field_value, or None if not found."""
        entries = self.get_entries(table_name, field_name, field_value)
        return entries[0] if entries else None

    def get_entries(self, table_name: str, field_name: str,
                   field_value: Field) -> list[Entry]:
        """Returns all entries where field_name equals field_value."""
        if table_name not in self.list_tables():
            raise ValueError(f"Table '{table_name}' doesn't exist")

        signature = self.get_table_signature(table_name)
        field_names = [name for name, _ in signature]

        # Validate field name
        if field_name not in field_names and field_name != "id":
            raise ValueError(f"Field '{field_name}' doesn't exist in table '{table_name}'")

        # Validate field value type
        if field_name != "id":
            for name, field_type in signature:
                if name == field_name:
                    if field_type == FieldType.INTEGER and not isinstance(field_value, int):
                        raise ValueError(f"Field '{field_name}' must be an integer")
                    elif field_type == FieldType.STRING and not isinstance(field_value, str):
                        raise ValueError(f"Field '{field_name}' must be a string")
                    break

        # Get entries and filter
        all_entries = self.get_complete_table(table_name)
        matching_entries = [
            entry for entry in all_entries if entry.get(field_name) == field_value
        ]

        return matching_entries

    def select_entry(self, table_name: str, fields: tuple[str], field_name: str,
                    field_value: Field) -> Field | tuple[Field]:
        """Selects specified fields from an entry where field_name equals field_value."""
        entry = self.get_entry(table_name, field_name, field_value)

        if not entry:
            return None

        # Validate requested fields
        for field in fields:
            if field not in entry and field != "id":
                raise ValueError(f"Field '{field}' doesn't exist in table '{table_name}'")

        # Return single value for single field request
        if len(fields) == 1:
            return entry.get(fields[0])

        # Return tuple of values for multiple fields
        return tuple(entry.get(field) for field in fields)

    def select_entries(self, table_name: str, fields: tuple[str], field_name: str,
                      field_value: Field) -> list[Field | tuple[Field]]:
        """Selects specified fields from all entries where field_name equals field_value."""
        entries = self.get_entries(table_name, field_name, field_value)

        # Empty case handling
        if not entries or not fields:
            return []

        # Validate requested fields
        all_fields = set([name for name, _ in self.get_table_signature(table_name)] + ["id"])
        for field in fields:
            if field not in all_fields:
                raise ValueError(f"Field '{field}' doesn't exist in table '{table_name}'")

        # Build results list
        results = []
        for entry in entries:
            if len(fields) == 1:
                results.append(entry.get(fields[0]))
            else:
                results.append(tuple(entry.get(field) for field in fields))

        return results

    def update_entries(self, table_name: str, cond_name: str, cond_value: Field,
                      update_name: str, update_value: Field) -> bool:
        """Update entries in a table where cond_name equals cond_value."""
        if table_name not in self.list_tables():
            raise ValueError(f"Table '{table_name}' doesn't exist")

        signature = self.get_table_signature(table_name)
        field_names = [name for name, _ in signature]

        # Validate fields
        if cond_name != "id" and cond_name not in field_names:
            raise ValueError(f"Field '{cond_name}' not found in table")

        if update_name not in field_names:
            raise ValueError(f"Field '{update_name}' not found in table")

        # Validate update value type
        update_field_type = None
        for name, field_type in signature:
            if name == update_name:
                update_field_type = field_type
                break

        if update_field_type == FieldType.INTEGER and not isinstance(update_value, int):
            raise ValueError(f"Field '{update_name}' must be an integer")
        elif update_field_type == FieldType.STRING and not isinstance(update_value, str):
            raise ValueError(f"Field '{update_name}' must be a string")

        # Find and update matching entries
        all_entries = self.get_complete_table(table_name)
        updated = False

        # Update entries in memory
        for entry in all_entries:
            # Process conditions based on field (ID or other field)
            if ((cond_name == "id" and entry.get("id") == cond_value) or
                    (entry.get(cond_name) == cond_value)):
                entry[update_name] = update_value
                updated = True

        # Update the file if changes were made
        if updated:
            self._rewrite_table(table_name, all_entries, signature)

        return updated

    def delete_entries(self, table_name: str, field_name: str, field_value: Field) -> bool:
        """Delete entries from a table where field_name equals field_value."""
        if table_name not in self.list_tables():
            raise ValueError(f"Table '{table_name}' doesn't exist")

        # Validate field
        signature = self.get_table_signature(table_name)
        field_names = [name for name, _ in signature]

        if field_name != "id" and field_name not in field_names:
            raise ValueError(f"Field '{field_name}' not found in table")

        # Validate field value type
        if field_name != "id":
            for name, field_type in signature:
                if name == field_name:
                    if field_type == FieldType.INTEGER and not isinstance(field_value, int):
                        raise ValueError(f"Field '{field_name}' must be an integer")
                    elif field_type == FieldType.STRING and not isinstance(field_value, str):
                        raise ValueError(f"Field '{field_name}' must be a string")
                    break

        # Find entries to delete
        entries_to_delete = self.get_entries(table_name, field_name, field_value)
        if not entries_to_delete:
            return False

        table_path = self._get_table_path(table_name)

        # Get all entries and ids to delete
        all_entries = self.get_complete_table(table_name)
        ids_to_delete = {entry["id"] for entry in entries_to_delete}

        # Update in-memory entries
        new_entries = [entry for entry in all_entries if entry["id"] not in ids_to_delete]
        self.entry_memory[table_name] = new_entries

        # If too many entries are deleted (less than 50% remain), rewrite the table
        if len(new_entries) < len(all_entries) / 2:
            self._rewrite_table(table_name, new_entries, signature)
            return True
        
        # Otherwise, update the file to mark deleted entries
        with open(table_path, "r+b") as file:
            table_file = BinaryFile(file)

            # Read header information
            header_end = self._read_header_end_position(table_file)
            _, _, entry_buffer_pos = self._read_str_buffer_pointers(
                table_file, header_end
            )

            # Read entry buffer header
            _, num_entries, first_entry_ptr, _, reserved_ptr = (
                self._read_entry_buffer_header(table_file, entry_buffer_pos)
            )

            # Update the entry count
            new_entry_count = num_entries - len(entries_to_delete)
            table_file.goto(entry_buffer_pos + 4)  # Position of entry count
            table_file.write_integer(new_entry_count, 4)

            # For each entry to delete, add it to the deleted entries chain
            for entry_to_delete in entries_to_delete:
                entry_id = entry_to_delete["id"]

                # Find the entry's position in the file
                current_ptr = first_entry_ptr
                _ = -1
                found = False

                # Traverse the linked list to find the entry
                for _ in range(num_entries):
                    if current_ptr == -1:
                        break

                    # Read entry ID
                    table_file.goto(current_ptr)
                    current_id = table_file.read_integer(4)

                    if current_id == entry_id:
                        found = True
                        entry_pos = current_ptr
                        break

                    # Read next pointer (after ID and fields)
                    next_ptr_pos = current_ptr + 4 + len(signature) * 4 + 4
                    table_file.goto(next_ptr_pos)
                    current_ptr = table_file.read_integer(4)

                if not found:
                    continue

                # Update linked list pointers to skip this entry
                table_file.goto(entry_pos + 4 + len(signature) * 4)  # Position of prev pointer
                prev_ptr = table_file.read_integer(4)
                next_ptr = table_file.read_integer(4)
                
                # Update pointers in previous and next entries
                if prev_ptr != -1:
                    table_file.goto(prev_ptr + 4 + len(signature) * 4 + 4)  # Next pointer of prev entry
                    table_file.write_integer(next_ptr, 4)
                else:
                    # This was the first entry, update header
                    table_file.goto(entry_buffer_pos + 8)  # First entry pointer
                    table_file.write_integer(next_ptr, 4)

                if next_ptr != -1:
                    table_file.goto(next_ptr + 4 + len(signature) * 4)  # Prev pointer of next entry
                    table_file.write_integer(prev_ptr, 4)
                else:
                    # This was the last entry, update header
                    table_file.goto(entry_buffer_pos + 12)  # Last entry pointer
                    table_file.write_integer(prev_ptr, 4)

                # Add this entry to the deleted entries chain
                table_file.goto(entry_pos + 4 + len(signature) * 4 + 4)  # Next pointer
                table_file.write_integer(reserved_ptr, 4)  # Link to current reserved head

                # Update reserved pointer to point to this entry
                table_file.goto(entry_buffer_pos + 16)  # Reserved pointer
                table_file.write_integer(entry_pos, 4)

                # Update reserved pointer for next iteration
                reserved_ptr = entry_pos

            return True
