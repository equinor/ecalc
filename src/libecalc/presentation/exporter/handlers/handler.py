import abc
import io
import sys
import typing
from pathlib import Path


class Handler(abc.ABC):
    @abc.abstractmethod
    def handle(self, grouped_row_based_data: dict[str, list[str]]):
        """Agnostic data handler, should handle row based data with an ID
        :param name: the group representing the row based data, an ID, if relevant
        :param grouped_row_based_data:
        :return:
        """
        pass


class StreamHandler(Handler):
    """Handle groups of data to the same stream."""

    def __init__(self, stream: typing.TextIO = sys.stdout, emit_name: bool = False):
        self.stream = stream
        self.emit_name = emit_name

    def handle(self, grouped_row_based_data: dict[str, list[str]]):
        for group_name, rows in grouped_row_based_data.items():
            if self.emit_name:
                self.stream.write("\n")
                self.stream.write(group_name)
                self.stream.write("\n\n")

            for row in rows:
                self.stream.write(row)
                self.stream.write("\n")


class MultiStreamHandler(Handler):
    """Handle groups of data to separate streams."""

    def __init__(self, streams: dict[str, typing.TextIO]):
        self.streams = streams

    def handle(self, grouped_row_based_data: dict[str, list[str]]):
        for group_name, rows in grouped_row_based_data.items():
            self.streams[group_name] = io.StringIO()
            for row in rows:
                self.streams[group_name].write(row)
                self.streams[group_name].write("\n")


class FileHandler(Handler):
    """Write groups of data to same file."""

    def __init__(self, path: Path, prefix: str, suffix: str, extension: str):
        self.path = path
        self.prefix = prefix
        self.suffix = suffix
        self.extension = extension

    def handle(self, grouped_row_based_data: dict[str, list[str]]):
        with open(self.path / f"{self.prefix}{self.suffix}{self.extension}", "w") as file:
            for rows in grouped_row_based_data.values():
                for row in rows:
                    file.write(row + "\n")


class MultiFileHandler(Handler):
    """Write groups of data to separate files."""

    def __init__(self, path: Path, prefix: str, suffix: str, extension: str):
        self.path = path
        self.prefix = prefix
        self.suffix = suffix
        self.extension = extension

    def handle(self, grouped_row_based_data: dict[str, list[str]]):
        for group_name, rows in grouped_row_based_data.items():
            with open(self.path / f"{self.prefix}.{group_name}{self.suffix}{self.extension}", "w") as file:
                for row in rows:
                    file.write(row + "\n")
