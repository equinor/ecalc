import enum
import re
from dataclasses import dataclass
from datetime import date
from textwrap import indent
from typing import Any, Dict, List, Optional, Tuple, Union

import yaml
from pydantic import ValidationError as PydanticValidationError
from pydantic_core import ErrorDetails
from typing_extensions import Self
from yaml import Dumper, Mark

from libecalc.common.logger import logger
from libecalc.presentation.yaml.yaml_entities import Resource, YamlDict, YamlList
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords

Loc = Tuple[Union[int, str], ...]

CUSTOM_MESSAGES = {
    "missing": "This keyword is missing, it is required",
    "extra_forbidden": "This is not a valid keyword",
}


def _get_position_in_file_message(mark: Mark) -> str:
    message = f"YAML object starting on line {mark.line + 1}"
    if mark.name is not None and mark.name != "":
        message += f" in {mark.name}"
    return message + "\n"


class ValidationError(Exception):
    pass


def dict_node_representer(dumper: Dumper, data):
    return dumper.represent_dict(dict(data))


yaml.add_representer(YamlDict, dict_node_representer)


def list_node_representer(dumper: Dumper, data):
    return dumper.represent_list(list(data))


yaml.add_representer(YamlList, list_node_representer)


def _remove_root_key(error_loc: Loc) -> List[Union[int, str]]:
    return [key for key in error_loc if key != "__root__"]


def _mark_error_lines(yaml_text: str, locs: List[Loc]) -> str:
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


class DumpFlowStyle(enum.Enum):
    INLINE = True
    BLOCK = False


class DataValidationError(ValidationError):
    """A general data validation error. Should be used with yaml-read data to output context to the error."""

    def __init__(
        self,
        data: Optional[Union[Dict[str, Any], YamlDict]],
        message: str,
        error_locs: Optional[List[Loc]] = None,
        error_key: Optional[str] = None,
        dump_flow_style: Optional[DumpFlowStyle] = None,
    ):
        super().__init__(message)
        self.message = message
        extended_message = "\nError in object\n"

        if data is not None:
            if error_locs is None and error_key is not None:
                error_locs = [(error_key,)]

            position_in_file_message = ""
            try:
                position_in_file_message = _get_position_in_file_message(data.start_mark)
            except AttributeError as e:
                logger.exception(e)
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


date_repr_pattern = r"datetime\.date\(([0-9]{4}),\s([0-9]{1,2}),\s([0-9]{1,2})\)"
date_repr_regex = re.compile(date_repr_pattern)


@dataclass
class Location:
    keys: List[Union[str, int, date]]

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
                path += f".{x.strftime('%Y-%m-%d')}"
            else:
                raise TypeError("Unexpected type")
        return path

    @classmethod
    def _parse_date(cls, key: str) -> Union[date, str]:
        date_matches = date_repr_regex.fullmatch(key)
        try:
            year, month, day = date_matches.groups()
            return date(int(year), int(month), int(day))
        except ValueError:
            # If matches.groups() does not contain three values, or year,month,day can not be parsed as int
            logger.exception("Unable to parse date key, returning string instead")
            return key

    @classmethod
    def _parse_key(cls, key: Union[str, int]) -> Union[int, str, date]:
        if isinstance(key, str) and date_repr_regex.fullmatch(key) is not None:
            return cls._parse_date(key)
        return key

    @classmethod
    def from_pydantic_loc(cls, loc: Loc) -> Self:
        return cls([cls._parse_key(key) for key in loc])


@dataclass
class ModelValidationError:
    details: ErrorDetails
    data: Optional[Dict]

    @property
    def location(self) -> Location:
        return Location.from_pydantic_loc(self.details["loc"])

    @property
    def message(self):
        return self.details["msg"]

    @property
    def input(self):
        return self.details["input"]

    @property
    def yaml(self) -> Optional[str]:
        if self.data is None:
            return None

        return yaml.dump(self.data, sort_keys=False).strip()

    def __str__(self):
        msg = self.location.as_dot_separated()
        msg += f"\t{self.message}"
        return msg


class DtoValidationError(DataValidationError):
    """DTO validation error. Should be used in the case that we have a ValidationError from creating a DTO.
    Context to the error message will be added. The data provided should be yaml-read data.
    """

    def error_count(self):
        return self.validation_error.error_count()

    @staticmethod
    def _get_nested_data(data: Any, keys: Loc) -> Optional[Any]:
        current_data = data
        for key in keys:
            try:
                current_data = current_data[key]
            except (KeyError, TypeError):
                # KeyError if key not in dict, TypeError if current_data is None
                return None
        return current_data

    def _get_closest_data_with_key(self, loc: Loc, key: str) -> Optional[Dict]:
        for i in range(len(loc)):
            if i == 0:
                end_index = None
            else:
                end_index = -i
            nested_data = self._get_nested_data(data=self.data, keys=loc[:end_index])
            if isinstance(nested_data, dict) and key in nested_data:
                return nested_data

        return None

    def _get_context_data(self, loc: Loc) -> Optional[Dict]:
        # Try to get data with 'NAME' attribute
        component_data = self._get_closest_data_with_key(loc, key=EcalcYamlKeywords.name)
        if component_data is not None:
            return component_data

        if len(loc) > 1:
            # Get one level, works well for VARIABLES
            return self._get_nested_data(self.data, (loc[0],))

    def errors(self) -> List[ModelValidationError]:
        errors = []
        for error in custom_errors(e=self.validation_error, custom_messages=CUSTOM_MESSAGES):
            errors.append(
                ModelValidationError(
                    details=error,
                    data=self._get_context_data(loc=error["loc"]),
                )
            )
        return errors

    def __init__(
        self,
        data: Optional[Union[Dict[str, Any], YamlDict]],
        validation_error: PydanticValidationError,
        **kwargs,
    ):
        self.data = data
        self.validation_error = validation_error

        name = data.get(EcalcYamlKeywords.name)
        message_title = f"\n{name}:"
        messages = [message_title]

        errors = custom_errors(e=validation_error, custom_messages=CUSTOM_MESSAGES)
        error_locs = []

        try:
            for error in errors:
                error_locs.append(error["loc"])

                if data is not None:
                    messages.append(f"{error['msg']}")
                else:
                    messages.append(f"{name}:\n{error['msg']}")
        except Exception as e:
            logger.debug(f"Failed to add location specific error messages: {str(e)}")

        message = "\n".join(messages)
        super().__init__(data, message, error_locs=error_locs, **kwargs)


class ResourceValidationError(ValidationError):
    """Validation error for a resource. Currently, we are not doing anything with the resource data."""

    def __init__(self, resource: Resource, resource_name: str, message: str):
        resource_message = f"Resource with name '{resource_name}' contains errors.\n"
        resource_message += message
        super().__init__(resource_message)


class ValidationValueError(ValueError):
    """Error used to propagate an error up to a point where we have enough context to give a ValidationError.
    i.e. if you raise this error you should make sure there is an except ValidationValueError above somewhere.
    """

    def __init__(self, message: str, key: Optional[str] = None):
        self.key = key
        super().__init__(message)


def custom_errors(e: PydanticValidationError, custom_messages: Dict[str, str]) -> List[ErrorDetails]:
    """
    Customized pydantic validation errors, to give user more precise feedback.

    :param e: pydantic validation error
    :param custom_messages: custom error messages to overwrite pydantic standard messages
    :return: list of error details
    """
    new_errors: List[ErrorDetails] = []
    for error in e.errors():
        custom_message = custom_messages.get(error["type"])
        if custom_message:
            error_key_name = error["loc"][0].upper().replace("__root__", "General error")
            custom_message = error_key_name + ":\t" + custom_message
            ctx = error.get("ctx")
            error["msg"] = custom_message.format(**ctx) if ctx else custom_message
        new_errors.append(error)
    return new_errors
