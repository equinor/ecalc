import enum
from textwrap import indent
from typing import Any, Dict, List, Optional, Tuple, Union

import yaml
from pydantic import ValidationError as PydanticValidationError
from pydantic_core import ErrorDetails
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


class DtoValidationError(DataValidationError):
    """DTO validation error. Should be used in the case that we have a ValidationError from creating a DTO.
    Context to the error message will be added. The data provided should be yaml-read data.
    """

    def __init__(
        self,
        data: Optional[Union[Dict[str, Any], YamlDict]],
        validation_error: PydanticValidationError,
        **kwargs,
    ):
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
