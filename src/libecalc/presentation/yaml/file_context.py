from dataclasses import dataclass
from typing import Self

from libecalc.presentation.yaml.yaml_node import YamlDict


@dataclass
class FileMark:
    line_number: int
    column_number: int

    def __str__(self) -> str:
        return f" line {self.line_number}, column {self.column_number}"


@dataclass
class FileContext:
    start: FileMark
    end: FileMark | None = None
    name: str | None = None

    def __str__(self) -> str:
        file_context_string = ""
        if self.name is not None:
            file_context_string += f" in '{self.name}',"

        file_context_string += str(self.start)

        return file_context_string

    @classmethod
    def from_yaml_dict(cls, data: YamlDict) -> Self:
        if not hasattr(data, "end_mark") or not hasattr(data, "start_mark"):
            return None

        # This only works with our implementation of pyyaml read
        # In the future, we can move this logic into PyYamlYamlModel with a better interface in YamlValidator.
        # Specifically with our own definition of the returned data in each property in YamlValidator.
        start_mark = data.start_mark
        end_mark = data.end_mark
        return FileContext(
            start=FileMark(
                line_number=start_mark.line + 1,
                column_number=start_mark.column,
            ),
            end=FileMark(
                line_number=end_mark.line + 1,
                column_number=end_mark.column,
            ),
        )
