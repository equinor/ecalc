from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, JsonValue, WithJsonSchema
from pydantic.fields import FieldInfo

from libecalc.common.version import Version
from libecalc.version import current_yaml_version

MAJOR_VERSION_PATTERN = r"^\d+$"


def _parse_major_version(value: int | str) -> int:
    major_version: int = 0

    match value:
        case bool():
            raise ValueError(f"Invalid yaml version '{value}'. Expected a major version integer, e.g. 1, 2, 3.")
        case int():
            major_version = value
        case str():
            if re.fullmatch(MAJOR_VERSION_PATTERN, value.strip()):
                major_version = int(value.strip())

    if major_version < 1 or major_version > current_yaml_version().major:
        raise ValueError(
            f"Invalid yaml version '{major_version}'. Expected a major version integer, greater than 0 and less than or equal to {current_yaml_version().major}. "
        )
    return major_version


YamlMajorVersion = Annotated[
    int,
    BeforeValidator(_parse_major_version),
    WithJsonSchema({"type": "integer", "minimum": 1, "maximum": current_yaml_version().major}),
]
"""
A pydantic-compatible field type for the declared document YAML_VERSION.

Only the major version is tracked here: YAML_VERSION: 2 means "any 2.x.y", matching how root
element availability is defined below. The exact X.Y.Z semantic versions used for
available_since/deprecated_since/removed_since are set once by the library maintainer per
root element, whereas the document YAML_VERSION is a range a user declares, so it intentionally
does not represent minor or patch.
"""

# Schema generations referred to elsewhere as "legacy" (v1), "transitional" (v2, where legacy and
# new root elements can both be used)
# To make it easy to spot changes, add all versions here in order to easily refer to it correctly,
# and to easy find all changes related to a version later, manually or automatically
V1 = Version(1, 0, 0)
V2 = Version(2, 0, 0)

DEFAULT_YAML_VERSION = V1.major

AVAILABLE_SINCE_KEY = "available_since"
DEPRECATED_SINCE_KEY = "deprecated_since"
REMOVED_SINCE_KEY = "removed_since"


def yaml_element_lifecycle(
    available_since: Version | None = None,
    deprecated_since: Version | None = None,
    removed_since: Version | None = None,
) -> dict[str, JsonValue]:
    """
    Build the json_schema_extra for a root element Field(...) call, marking its lifecycle.

    Root elements without an available_since marker are implicitly available since V1.
    Versions are stored as plain X.Y.Z strings so the extra dict stays JSON-friendly.
    """
    extra: dict[str, JsonValue] = {}
    if available_since is not None:
        extra[AVAILABLE_SINCE_KEY] = str(available_since)
    if deprecated_since is not None:
        extra[DEPRECATED_SINCE_KEY] = str(deprecated_since)
    if removed_since is not None:
        extra[REMOVED_SINCE_KEY] = str(removed_since)
    return extra


@dataclass(frozen=True)
class YamlElementLifecycle:
    available_since: Version
    deprecated_since: Version | None
    removed_since: Version | None


def get_yaml_element_lifecycle(field_info: FieldInfo) -> YamlElementLifecycle:
    """Get the lifecycle of a root element field, defaulting to available since V1."""
    extra = field_info.json_schema_extra if isinstance(field_info.json_schema_extra, dict) else {}

    def _parse(key: str) -> Version | None:
        value = extra.get(key)
        return Version.from_string(value) if isinstance(value, str) else None

    return YamlElementLifecycle(
        available_since=_parse(AVAILABLE_SINCE_KEY) or V1,
        deprecated_since=_parse(DEPRECATED_SINCE_KEY),
        removed_since=_parse(REMOVED_SINCE_KEY),
    )


def is_available_for_version(field_info: FieldInfo, version: int) -> bool:
    """Whether a root element field is available for the given declared yaml document major version."""
    lifecycle = get_yaml_element_lifecycle(field_info)
    if version < lifecycle.available_since.major:
        return False
    if lifecycle.removed_since is not None and version >= lifecycle.removed_since.major:
        return False
    return True


def get_root_field_names(model: type[BaseModel], version: int) -> set[str]:
    """Get the names of root elements available for the given declared yaml document major version."""
    return {
        field_name
        for field_name, field_info in model.model_fields.items()
        if is_available_for_version(field_info, version)
    }


def get_unavailable_field_names(model: type[BaseModel], version: int, field_names: Iterable[str]) -> set[str]:
    """Of the given root element field names, return those not available for the given yaml document version."""
    return {
        field_name
        for field_name in field_names
        if field_name in model.model_fields and not is_available_for_version(model.model_fields[field_name], version)
    }
