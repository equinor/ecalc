from dataclasses import dataclass


@dataclass
class FileMark:
    line_number: int
    column_number: int

    def __str__(self) -> str:
        return f" line {self.line_number}, column {self.column_number}"


@dataclass
class FileContext:
    name: str
    start: FileMark
    end: FileMark | None = None

    def __str__(self) -> str:
        file_context_string = ""
        file_context_string += f" in '{self.name}',"

        file_context_string += str(self.start)

        return file_context_string
