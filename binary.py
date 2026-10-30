from typing import BinaryIO


class BinaryFile:
    """
    Utility class to handle binary file operations, including reading and writing
    integers and strings.
    """
    
    def __init__(self, file: BinaryIO):
        """Initialize with a binary file object."""
        self.file = file

    def goto(self, pos: int) -> None:
        """Move the file cursor to a specific position."""
        try:
            if pos >= 0:
                self.file.seek(pos, 0)  # Absolute positioning
            else:
                self.file.seek(pos, 2)  # Relative to end of file
        except Exception as e:
            raise ValueError(f"Invalid file position: {pos}") from e

    def get_size(self) -> int:
        """Get the total size of the file in bytes."""
        initial_position = self.file.tell()
        self.file.seek(0, 2)  # Move cursor to end of file
        size = self.file.tell()
        self.file.seek(initial_position)  # Restore original position
        return size

    def write_integer(self, n: int, size: int) -> int:
        """Write an integer of a given byte size in little-endian format."""
        if n == 0xFFFFFFFF:  # Special case for -1 equivalent
            self.file.write(b'\xFF' * 4)
        else:
            self.file.write(n.to_bytes(size, byteorder="little", signed=True))
        return size

    def write_integer_to(self, n: int, size: int, pos: int) -> int:
        """Write an integer at a specific file position without changing the cursor."""
        current_position = self.file.tell()
        self.goto(pos)
        bytes_written = self.write_integer(n, size)
        self.goto(current_position)  # Restore cursor position
        return bytes_written

    def write_string(self, s: str) -> int:
        """Write a UTF-8 string with a 2-byte length prefix."""
        encoded_string = s.encode("utf-8")
        length_prefix = len(encoded_string).to_bytes(2, "little", signed=False)  # Always positive
        self.file.write(length_prefix + encoded_string)
        return len(length_prefix) + len(encoded_string)

    def write_string_to(self, s: str, pos: int) -> int:
        """Write a string at a specific file position without changing the cursor."""
        current_position = self.file.tell()
        self.goto(pos)
        bytes_written = self.write_string(s)
        self.goto(current_position)  # Restore cursor position
        return bytes_written

    def write_string_without_size(self, s: str) -> None:
        """Write a UTF-8 string to the file without a length prefix."""
        self.file.write(s.encode("utf-8"))

    def read_integer(self, size: int) -> int:
        """Read an integer of a given byte size from the current position."""
        bytes_sequence = self.file.read(size)
        return int.from_bytes(bytes_sequence, byteorder='little', signed=True)

    def read_integer_from(self, size: int, pos: int) -> int:
        """Read an integer from a specific position without changing the cursor."""
        current_position = self.file.tell()
        self.goto(pos)
        value = self.read_integer(size)
        self.goto(current_position)  # Restore cursor position
        return value

    def read_string(self) -> str:
        """Read a UTF-8 string with a 2-byte length prefix from the current position."""
        length_bytes = self.file.read(2)  # Read string length
        string_length = int.from_bytes(length_bytes, byteorder='little', signed=False)
        string_bytes = self.file.read(string_length)
        return string_bytes.decode("utf-8")
    
    def read_string_without_size(self) -> str:
        """Read a UTF-8 string without a length prefix from the current position."""
        string_bytes = self.file.read()
        return string_bytes.decode("utf-8")

    def read_string_from(self, pos: int) -> str:
        """Read a UTF-8 string from a specific position without changing the cursor."""
        current_position = self.file.tell()
        self.goto(pos)
        value = self.read_string()
        self.goto(current_position)  # Restore cursor position
        return value
    
    def tell_position(self) -> int:
        """Return the current position of the file cursor."""
        return self.file.tell()