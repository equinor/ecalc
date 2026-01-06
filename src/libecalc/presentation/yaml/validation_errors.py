import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date
from typing import Self, Union

import yaml
from pydantic import ValidationError as PydanticValidationError
from pydantic_core import ErrorDetails
from yaml import Dumper

from libecalc.common.logger import logger
from libecalc.presentation.yaml.file_context import FileContext
from libecalc.presentation.yaml.yaml_node import YamlDict, YamlList

PydanticKey = Union[int, str]
PydanticLoc = tuple[PydanticKey, ...]

CUSTOM_MESSAGES = {
    "missing": "This keyword is missing, it is required",
    "extra_forbidden": "This is not a valid keyword",
    "string_pattern_mismatch": "The string/name contains illegal characters. Allowed characters are: {pattern}. "
    "A good start can be to check the string/name for space, which is not allowed.",
    "union_tag_not_found": "The keyword {discriminator} is missing, it is required.",
}


@dataclass
class Location:
    keys: Sequence[str | int | date]

    def is_empty(self) -> bool:
        return len(self.keys) == 0

    def as_dot_separated(self) -> str:
        path = ""
        for i, x in enumerate(self.keys):
            if isinstance(x, str):
                if i > 0:
                    path += "."
                path += x
            elif isinstance(x, int):
                path += f"[{x}]"
            elif isinstance(x, date):
                path += f".{self._date_to_string(x)}"
            else:
                raise TypeError("Unexpected type")
        return path

    @classmethod
    def _date_to_string(cls, d: date) -> str:
        return d.strftime("%Y-%m-%d")

    @classmethod
    def _parse_date(cls, key: str) -> date | str:
        date_matches = date_repr_regex.fullmatch(key)
        try:
            year, month, day = date_matches.groups()
            return date(int(year), int(month), int(day))
        except ValueError:
            # If matches.groups() does not contain three values, or year,month,day can not be parsed as int
            logger.exception("Unable to parse date key, returning string instead")
            return key

    @classmethod
    def _parse_key(cls, key: str | int) -> int | str | date:
        if isinstance(key, str) and date_repr_regex.fullmatch(key) is not None:
            return cls._parse_date(key)
        return key

    @classmethod
    def from_pydantic_loc(cls, loc: PydanticLoc) -> Self:
        return cls([cls._parse_key(key) for key in loc])


def dict_node_representer(dumper: Dumper, data):
    return dumper.represent_dict(dict(data))


yaml.add_representer(YamlDict, dict_node_representer)


def list_node_representer(dumper: Dumper, data):
    return dumper.represent_list(list(data))


yaml.add_representer(YamlList, list_node_representer)


date_repr_pattern = r"datetime\.date\(([0-9]{4}),\s([0-9]{1,2}),\s([0-9]{1,2})\)"
date_repr_regex = re.compile(date_repr_pattern)


@dataclass
class ModelValidationError:
    location: Location
    message: str
    file_context: FileContext | None
    data: dict | None = None
    name: str | None = None

    @property
    def yaml(self) -> str | None:
        if self.data is None:
            return None

        return yaml.dump(self.data, sort_keys=False).strip()

    def __str__(self) -> str:
        msg = ""
        if self.file_context is not None and self.file_context.start is not None:
            msg += f"Object starting on line {self.file_context.start.line_number}\n"
        yaml = self.yaml
        if yaml is not None:
            msg += "...\n"
            msg += yaml
            msg += "\n...\n\n"

        if not self.location.is_empty():
            msg += f"Location: {self.location.as_dot_separated()}\n"

        if self.name is not None:
            msg += f"Name: {self.name}\n"

        msg += f"Message: {self.message}\n"
        return msg


def custom_errors(e: PydanticValidationError) -> list[ErrorDetails]:
    """
    Customized pydantic validation errors, to give user more precise feedback.

    :param e: pydantic validation error
    :param custom_messages: custom error messages to overwrite pydantic standard messages
    :return: list of error details
    """
    new_errors: list[ErrorDetails] = []
    for error in e.errors():
        custom_message = CUSTOM_MESSAGES.get(error["type"])
        if custom_message:
            ctx = error.get("ctx")
            error["msg"] = custom_message.format(**ctx) if ctx else custom_message
        new_errors.append(error)
    return new_errors
