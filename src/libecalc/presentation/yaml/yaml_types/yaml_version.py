from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Annotated, Any, cast

from pydantic import BaseModel, BeforeValidator, JsonValue, WithJsonSchema
from pydantic.fields import Field, FieldInfo

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
V3 = Version(3, 0, 0)
V4 = Version(4, 0, 0)

DEFAULT_YAML_VERSION = V1.major
LATEST_YAML_VERSION = current_yaml_version().major

AVAILABLE_SINCE_KEY = "available_since"
DEPRECATED_SINCE_KEY = "deprecated_since"
REMOVED_SINCE_KEY = "removed_since"
CHANGED_IN_KEY = "changed_in"
REQUIRED_KEY = "required"
REPLACED_BY_KEY = "replaced_by"


@dataclass(frozen=True)
class ChangeEntry:
    version: Version
    description: str


def removed_field(
    title: str,
    removed_in: Version,
    message: str | None = None,
    available_since: Version | None = None,
    replaced_by: tuple[str, ...] | None = None,
) -> Any:
    """
    Use this field type to annotate removed fields for documentation only.

    replaced_by is the path to the element replacing the removed one, e.g. ("DEFINITIONS", "COMPRESSOR_MODELS").
    It is shown as a breadcrumb in the error message, and used to link to the element in the docs.
    """
    replaced_by_message = f"Use {' > '.join(replaced_by)} instead." if replaced_by else None
    full_message = " ".join(part for part in (message, replaced_by_message) if part)

    def rejected_with(msg: str) -> BeforeValidator:
        def reject(_value: Any) -> Any:
            raise ValueError(msg)

        return BeforeValidator(reject)

    field = cast(
        FieldInfo,
        cast(
            object,
            Field(
                default=None,
                title=title,
                description=f"Removed in V{removed_in.major}: {full_message}",
                json_schema_extra={
                    **yaml_element_lifecycle(
                        available_since=available_since,
                        removed_since=removed_in,
                        changed_in=[(removed_in, message)] if message else None,
                        for_documentation_only=True,
                    ),
                    "deprecationMessage": full_message,
                    **({REPLACED_BY_KEY: list(replaced_by)} if replaced_by else {}),
                },
            ),
        ),
    )
    field.metadata.append(rejected_with(msg=full_message))
    return field


def yaml_element_lifecycle(
    available_since: Version | None = None,
    deprecated_since: Version | None = None,
    removed_since: Version | None = None,
    changed_in: Iterable[tuple[Version, str]] | None = None,
    required: bool = False,
    for_documentation_only: bool = False,
) -> dict[str, JsonValue]:
    """
    Build the json_schema_extra for a root element Field(...) call, marking its lifecycle.

    Root elements without an available_since marker are implicitly available since V1.
    Versions are stored as plain X.Y.Z strings so the extra dict stays JSON-friendly.

    required marks a root element that must be explicitly present in the yaml for every version it's
    available in, e.g. FUEL_TYPES and INSTALLATIONS in V1/V2. This is separate from available_since/
    removed_since so an element can be required while available, then disallowed entirely once removed,
    without pydantic itself ever treating the field as required (it still needs a default for versions
    where it's absent, e.g. V3).

    changed_in lists (version, description) pairs describing a behavioral change to the element that
    wasn't an addition, deprecation or removal, e.g. [(V4, "Added support to also load from curve.")].

    If an element is only still available for documentation purposes, mark it as for_documentation_only. This will make the element fail validation for any version, so it is not allowed in the yaml for that version or any later version.
    """
    extra: dict[str, JsonValue] = {}
    if available_since is not None:
        extra[AVAILABLE_SINCE_KEY] = str(available_since)
    if deprecated_since is not None:
        extra[DEPRECATED_SINCE_KEY] = str(deprecated_since)
    if removed_since is not None:
        extra[REMOVED_SINCE_KEY] = str(removed_since)
    if changed_in:
        extra[CHANGED_IN_KEY] = [
            {"version": str(version), "description": description} for version, description in changed_in
        ]
    if required:
        extra[REQUIRED_KEY] = True

    # This makes the given element fail for any version. It is used to mark elements as removed in a version, so they are not allowed in the yaml for that version or any later version.
    if for_documentation_only:
        extra["not"] = {"const": "Prohibited"}

    return extra


@dataclass(frozen=True)
class YamlElementLifecycle:
    available_since: Version
    deprecated_since: Version | None
    removed_since: Version | None
    changed_in: tuple[ChangeEntry, ...]
    required: bool = False
    replaced_by: tuple[str, ...] = ()


def _parse_lifecycle_extra(extra: dict[str, JsonValue]) -> YamlElementLifecycle:
    def _parse(key: str) -> Version | None:
        value = extra.get(key)
        return Version.from_string(value) if isinstance(value, str) else None

    def _parse_changed_in() -> tuple[ChangeEntry, ...]:
        value = extra.get(CHANGED_IN_KEY)
        if not isinstance(value, list):
            return ()
        changes: list[ChangeEntry] = []
        for entry in value:
            if not isinstance(entry, dict):
                continue
            version = entry.get("version")
            description = entry.get("description")
            if isinstance(version, str) and isinstance(description, str):
                changes.append(ChangeEntry(version=Version.from_string(version), description=description))
        return tuple(changes)

    def _parse_replaced_by() -> tuple[str, ...]:
        value = extra.get(REPLACED_BY_KEY)
        if not isinstance(value, list):
            return ()
        return tuple(item for item in value if isinstance(item, str))

    return YamlElementLifecycle(
        available_since=_parse(AVAILABLE_SINCE_KEY) or V1,
        deprecated_since=_parse(DEPRECATED_SINCE_KEY),
        removed_since=_parse(REMOVED_SINCE_KEY),
        changed_in=_parse_changed_in(),
        required=bool(extra.get(REQUIRED_KEY, False)),
        replaced_by=_parse_replaced_by(),
    )


def get_yaml_element_lifecycle(field_info: FieldInfo) -> YamlElementLifecycle:
    """Get the lifecycle of a root element field, defaulting to available since V1."""
    extra = field_info.json_schema_extra if isinstance(field_info.json_schema_extra, dict) else {}
    return _parse_lifecycle_extra(extra)


def get_model_lifecycle(model: type[BaseModel]) -> YamlElementLifecycle:
    """
    Get the lifecycle of a discriminated union variant model (e.g. one tab of a TYPE-discriminated
    root element), defaulting to available since V1.

    Unlike a root element, a variant isn't a Field — it's set directly on the model's own
    model_config, e.g.:
        model_config = ConfigDict(json_schema_extra=yaml_element_lifecycle(available_since=V2))
    """
    extra = model.model_config.get("json_schema_extra")
    extra = extra if isinstance(extra, dict) else {}
    return _parse_lifecycle_extra(extra)


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


def is_required_for_version(field_info: FieldInfo, version: int) -> bool:
    """Whether a root element field must be explicitly present in the yaml for the given declared document version."""
    lifecycle = get_yaml_element_lifecycle(field_info)
    return lifecycle.required and is_available_for_version(field_info, version)


def get_required_field_names(model: type[BaseModel], version: int) -> set[str]:
    """Get the names of root elements that must be explicitly present in the yaml for the given document version."""
    return {
        field_name
        for field_name, field_info in model.model_fields.items()
        if is_required_for_version(field_info, version)
    }


Breadcrumb = tuple[str | int, ...]


def _iter_nested_models(value: object, path: Breadcrumb = ()) -> Iterable[tuple[Breadcrumb, BaseModel]]:
    """Depth-first yield of (path, model) for every pydantic model reachable from value, including value itself."""
    if isinstance(value, BaseModel):
        yield path, value
        for field_name, field_info in type(value).model_fields.items():
            alias = field_info.alias or field_name.upper()
            yield from _iter_nested_models(getattr(value, field_name), (*path, alias))
    elif isinstance(value, dict):
        for key, item in value.items():
            yield from _iter_nested_models(item, (*path, key))
    elif isinstance(value, list | tuple | set | frozenset):
        for index, item in enumerate(value):
            yield from _iter_nested_models(item, (*path, index))


def _format_breadcrumb(path: Breadcrumb) -> str:
    """Render a path as e.g. "PROCESS_PIPELINES > export_pipeline > PROCESS_UNITS[0] > SHAFT"."""
    parts: list[str] = []
    for segment in path:
        if isinstance(segment, int):
            parts[-1] = f"{parts[-1]}[{segment}]"
        else:
            parts.append(segment)
    return " > ".join(parts)


def get_unavailable_elements(root: object, version: int, path: Breadcrumb = ()) -> set[str]:
    """
    Find the breadcrumb path of every element explicitly set in the yaml that isn't available for the
    given declared document version, anywhere within root — not just among root's own fields.

    root can be a single model, or a container of models (e.g. a dict of PROCESS_PIPELINES), to scope
    the search to a subtree; path is prepended to every breadcrumb found, to describe where root itself
    sits in the full document, e.g. path=("PROCESS_PIPELINES",). This catches elements nested arbitrarily
    deep, e.g. SHAFT on a COMPRESSOR_PROCESS_UNIT inside PROCESS_PIPELINES, which get_unavailable_field_names
    alone can't see since it only inspects the fields of the single model it's given.
    """
    return {
        _format_breadcrumb((*model_path, type(model).model_fields[field_name].alias or field_name.upper()))
        for model_path, model in _iter_nested_models(root, path)
        for field_name in get_unavailable_field_names(type(model), version, model.model_fields_set)
    }
