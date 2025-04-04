import enum
import re
from dataclasses import dataclass
from datetime import date
from textwrap import indent
from typing import Any, Self, Union

import yaml
from pydantic import ValidationError as PydanticValidationError
from pydantic_core import ErrorDetails
from yaml import Dumper, Mark

from libecalc.common.logger import logger
from libecalc.presentation.yaml.file_context import FileContext
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
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


def _get_position_in_file_message(mark: Mark) -> str:
    message = f"Object starting on line {mark.line + 1}"
    if mark.name is not None and mark.name != "":
        message += f" in {mark.name}"
    return message + "\n"


@dataclass
class Location:
    keys: list[str | int | date]

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


class ValidationError(Exception):
    pass


def dict_node_representer(dumper: Dumper, data):
    return dumper.represent_dict(dict(data))


yaml.add_representer(YamlDict, dict_node_representer)


def list_node_representer(dumper: Dumper, data):
    return dumper.represent_list(list(data))


yaml.add_representer(YamlList, list_node_representer)


class DumpFlowStyle(enum.Enum):
    INLINE = True
    BLOCK = False


date_repr_pattern = r"datetime\.date\(([0-9]{4}),\s([0-9]{1,2}),\s([0-9]{1,2})\)"
date_repr_regex = re.compile(date_repr_pattern)


def _remove_root_key(error_loc: Location) -> list[int | str | date]:
    return [key for key in error_loc.keys if key != "__root__"]


def _mark_error_lines(yaml_text: str, locs: list[Location]) -> str:
    lines = yaml_text.split("\n")
    marked_lines = []
    for line in lines:
        first_error = locs[0]  # Only marking first error for now
        error_without_root = _remove_root_key(first_error)
        first_key = error_without_root[0]
        if line.strip().startswith(first_key.upper()):
            marked_lines.append(f"{' >'}{line}")
        else:
            marked_lines.append(f"  {line}")

    return "\n".join(marked_lines)


class DataValidationError(ValidationError):
    """A general data validation error. Should be used with yaml-read data to output context to the error."""

    def __init__(
        self,
        data: dict[str, Any] | YamlDict | None,
        message: str,
        error_locs: list[Location] | None = None,
        error_key: str | None = None,
        dump_flow_style: DumpFlowStyle | None = None,
    ):
        super().__init__(message)
        # self._message = message

        if data is not None and data.get(EcalcYamlKeywords.name) is not None:
            extended_message = f"Validation error in '{data.get(EcalcYamlKeywords.name)}'\n"
        else:
            extended_message = "Validation error\n"

        if data is not None:
            if error_locs is None and error_key is not None:
                error_locs = [Location(keys=[error_key])]

            position_in_file_message = ""
            try:
                position_in_file_message = _get_position_in_file_message(data.start_mark)
            except AttributeError:
                # This happens if the data passed to the exception has been parsed into a pydantic object, then dumped.
                # The file-context from the yaml reader is lost when the data has been parsed.
                pass

            yaml_dump = yaml.dump(
                data, default_flow_style=dump_flow_style.value if dump_flow_style is not None else None, sort_keys=False
            ).strip()
            indented_yaml = indent(yaml_dump, "    ")

            try:
                if error_locs is not None:
                    indented_yaml = _mark_error_lines(indented_yaml, error_locs)
                else:
                    logger.debug("No error locations to mark")
            except Exception as e:
                logger.debug(f"Could not mark error lines: {str(e)}")
                pass

            data_yaml = f"{indented_yaml}"
            extended_message += f"\n...\n{data_yaml}\n...\n\n{position_in_file_message}\n"

        extended_message += f"Error Message(s):\n{message}"
        self.extended_message = extended_message


@dataclass
class ModelValidationError:
    data: dict | None
    location: Location
    message: str
    file_context: FileContext | None

    @property
    def yaml(self) -> str | None:
        if self.data is None:
            return None

        return yaml.dump(self.data, sort_keys=False).strip()

    def __str__(self):
        msg = ""
        if self.file_context is not None:
            msg += f"Object starting on line {self.file_context.start.line_number}\n"
        yaml = self.yaml
        if yaml is not None:
            msg += "...\n"
            msg += yaml
            msg += "\n...\n\n"

        if not self.location.is_empty():
            msg += f"Location: {self.location.as_dot_separated()}\n"

        msg += f"Message: {self.message}\n"
        return msg


class DtoValidationError(DataValidationError):
    """DTO validation error. Should be used in the case that we have a ValidationError from creating a DTO.
    Context to the error message will be added. The data provided should be yaml-read data.
    """

    def error_count(self):
        return self.validation_error.error_count()

    @staticmethod
    def _get_nested_data(data: Any, keys: PydanticLoc) -> Any | None:
        current_data = data
        for key in keys:
            try:
                current_data = current_data[key]
            except (KeyError, TypeError):
                # KeyError if key not in dict, TypeError if current_data is None
                return None
        return current_data

    def _get_closest_data_with_key(self, loc: PydanticLoc, key: str) -> dict | None:
        for i in range(len(loc)):
            if i == 0:
                end_index = None
            else:
                end_index = -i
            nested_data = self._get_nested_data(data=self.data, keys=loc[:end_index])
            if isinstance(nested_data, dict) and key in nested_data:
                return nested_data

        return None

    def _get_context_data(self, loc: PydanticLoc) -> dict | None:
        # Try to get data with 'NAME' attribute
        component_data = self._get_closest_data_with_key(loc, key=EcalcYamlKeywords.name)
        if component_data is not None:
            return component_data

        if len(loc) > 1:
            # Get one level, works well for VARIABLES
            return self._get_nested_data(self.data, (loc[0],))

    def errors(self) -> list[ModelValidationError]:
        errors = []
        for error in custom_errors(e=self.validation_error, custom_messages=CUSTOM_MESSAGES):
            data = self._get_context_data(loc=error["loc"])
            errors.append(
                ModelValidationError(
                    location=Location.from_pydantic_loc(error["loc"]),
                    message=error["msg"],
                    file_context=FileContext.from_yaml_dict(data),
                    data=data,
                )
            )
        return errors

    def __init__(
        self,
        data: dict[str, Any] | YamlDict | None,
        validation_error: PydanticValidationError,
        **kwargs,
    ):
        self.data = data
        self.validation_error = validation_error

        messages = []

        errors = self.errors()
        error_locs = []
        for error in errors:
            error_locs.append(error.location)
            messages.append(f"{error}")

        message = "\n".join(messages)
        super().__init__(data, message, error_locs=error_locs, **kwargs)


class ValidationValueError(ValueError):
    """Error used to propagate an error up to a point where we have enough context to give a ValidationError.
    i.e. if you raise this error you should make sure there is an except ValidationValueError above somewhere.
    """

    def __init__(self, message: str, key: str | None = None):
        self.key = key
        super().__init__(message)


def custom_errors(e: PydanticValidationError, custom_messages: dict[str, str]) -> list[ErrorDetails]:
    """
    Customized pydantic validation errors, to give user more precise feedback.

    :param e: pydantic validation error
    :param custom_messages: custom error messages to overwrite pydantic standard messages
    :return: list of error details
    """
    new_errors: list[ErrorDetails] = []
    for error in e.errors():
        custom_message = custom_messages.get(error["type"])
        if custom_message:
            ctx = error.get("ctx")
            error["msg"] = custom_message.format(**ctx) if ctx else custom_message
        new_errors.append(error)
    return new_errors
