from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, PlainSerializer, WithJsonSchema
from pydantic.fields import FieldInfo

from libecalc.common.version import VERSION_FORMAT, Version


def _parse_version(value: Version | str) -> Version:
    return value if isinstance(value, Version) else Version.from_string(value)


YamlSemanticVersion = Annotated[
    Version,
    BeforeValidator(_parse_version),
    PlainSerializer(str, return_type=str),
    WithJsonSchema({"type": "string", "pattern": VERSION_FORMAT}),
]
"""A pydantic-compatible field type for Version, accepting and serializing X.Y.Z strings."""

# Schema baselines referred to elsewhere as "legacy" (v1) and "nextgen" (v2).
V1 = Version(1, 0, 0)
V2 = Version(2, 0, 0)

AVAILABLE_SINCE_KEY = "available_since"
DEPRECATED_SINCE_KEY = "deprecated_since"
REMOVED_SINCE_KEY = "removed_since"


def version_field_json_schema_extra(default: Version) -> dict[str, str]:
    """
    Build json_schema_extra for a Version field, rendering its default as a plain X.Y.Z string.

    Needed because pydantic's json schema generator does not apply the field's
    PlainSerializer when encoding the default value.
    """
    return {"default": str(default)}


def yaml_element_lifecycle(
    *,
    available_since: Version | None = None,
    deprecated_since: Version | None = None,
    removed_since: Version | None = None,
) -> dict[str, str]:
    """
    Build the json_schema_extra for a root element Field(...) call, marking its lifecycle.

    Root elements without an available_since marker are implicitly available since V1.
    Versions are stored as plain X.Y.Z strings so the extra dict stays JSON-friendly.
    """
    extra: dict[str, str] = {}
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


def is_available_for_version(field_info: FieldInfo, version: Version) -> bool:
    """Whether a root element field is available for the given yaml document version."""
    lifecycle = get_yaml_element_lifecycle(field_info)
    if version < lifecycle.available_since:
        return False
    if lifecycle.removed_since is not None and version >= lifecycle.removed_since:
        return False
    return True


def get_root_field_names(model: type[BaseModel], version: Version) -> set[str]:
    """Get the names of root elements available for the given yaml document version."""
    return {
        field_name
        for field_name, field_info in model.model_fields.items()
        if is_available_for_version(field_info, version)
    }
