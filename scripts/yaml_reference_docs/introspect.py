"""
Extract documentation data from Pydantic models.

Provides human-readable type labels, default values,
and child model extraction from type annotations.
"""

from enum import Enum
from typing import Any, get_origin, Annotated, get_args, Union, Literal

from pydantic import BaseModel
from pydantic.fields import FieldInfo
from pydantic_core import PydanticUndefined

from .mdx import strip_module_paths


def extract_child_models(annotation: Any) -> list[type[BaseModel]]:
    """Extract direct BaseModel subclasses from a type annotation."""
    while get_origin(annotation) is Annotated:
        annotation = get_args(annotation)[0]

    models: list[type[BaseModel]] = []
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        models.append(annotation)
        return models

    for arg in get_args(annotation):
        models.extend(extract_child_models(arg))

    return models


# --- Display names ---


def model_title(model: type[BaseModel]) -> str:
    """Get a display-friendly name for a model."""
    title = model.model_config.get("title")
    if title:
        return title
    name = model.__name__
    if name.startswith("Yaml"):
        name = name[4:]
    return name


# --- Type labels ---

_FRIENDLY: dict[type, str] = {
    str: "text",
    int: "integer",
    float: "number",
    bool: "true / false",
}


def _enum_label(enum_cls: type[Enum]) -> str:
    members = [str(m.value) for m in enum_cls]
    return ", ".join(members)


def _model_group_label(models: list[type[BaseModel]]) -> str:
    """
    Build a compact label from discriminator values when possible.

    Given [YamlSingleSpeed, YamlVariableSpeed], finds their shared
    discriminator field (type) and returns "SINGLE_SPEED | VARIABLE_SPEED"
    instead of "SingleSpeed | VariableSpeed".

    Falls back to joining model titles if no shared discriminator exists.
    """
    if len(models) < 2:
        return " ∣ ".join(model_title(m) for m in models)

    first_fields = set(models[0].model_fields.keys())
    for field_name in first_fields:
        values = []
        for m in models:
            fi = m.model_fields.get(field_name)
            if fi is None:
                break
            ann = fi.annotation
            while get_origin(ann) is Annotated:
                ann = get_args(ann)[0]
            if get_origin(ann) is not Literal:
                break
            args = get_args(ann)
            if len(args) != 1:
                break
            v = args[0]
            values.append(v.value if isinstance(v, Enum) else str(v))
        else:
            if len(set(values)) == len(models):
                return " ∣ ".join(values)

    return " ∣ ".join(model_title(m) for m in models)


def type_label(annotation: Any) -> str:
    """
    Convert a Python type annotation to a human-readable label for docs.

    Examples: str → "text", float → "number", list[MyModel] → "list[MyModel]",
    Literal["A", "B"] → "A ∣ B", Union[int, str] → "integer ∣ text"
    """

    while get_origin(annotation) is Annotated:
        annotation = get_args(annotation)[0]

    origin = get_origin(annotation)

    if origin is list:
        args = get_args(annotation)
        return f"list[{type_label(args[0])}]" if args else "list"

    if origin is dict:
        args = get_args(annotation)
        if len(args) == 2:
            return f"dict[{type_label(args[0])}, {type_label(args[1])}]"
        return "dict"

    if origin is Union or type(annotation).__name__ == "UnionType":
        args = [a for a in get_args(annotation) if a is not type(None)]

        # Detect temporal pattern: Union[T, dict[datetime, T]]
        # Strip Annotated wrappers (e.g. Tag("single"), Tag("temporal"))
        if len(args) == 2:
            stripped = []
            for a in args:
                while get_origin(a) is Annotated:
                    a = get_args(a)[0]
                stripped.append(a)

            dict_arg = next((a for a in stripped if get_origin(a) is dict), None)
            other_arg = next((a for a in stripped if get_origin(a) is not dict), None)
            if dict_arg and other_arg:
                dict_args = get_args(dict_arg)
                if len(dict_args) == 2 and dict_args[1] == other_arg:
                    inner = type_label(other_arg)
                    return f"{inner} · or per time period"

        simple_parts: list[str] = []
        model_types: list[type[BaseModel]] = []
        for a in args:
            child_models = extract_child_models(a)
            if child_models:
                model_types.extend(child_models)
            else:
                simple_parts.append(type_label(a))

        if simple_parts and len(model_types) >= 2:
            group_label = _model_group_label(model_types)
            return " ∣ ".join(simple_parts + [group_label])

        parts = [type_label(a) for a in args]
        return " ∣ ".join(parts)

    if origin is Literal:
        values = get_args(annotation)
        if not values:
            return "enum"
        formatted = []
        for v in values:
            formatted.append(v.value if isinstance(v, Enum) else str(v))
        if len(formatted) == 1:
            return formatted[0]
        if len(formatted) <= 8:
            return " ∣ ".join(formatted)
        return "enum"

    if origin is not None and isinstance(origin, type) and issubclass(origin, BaseModel):
        base_name = model_title(origin)
        args = get_args(annotation)
        if args:
            inner = ", ".join(type_label(a) for a in args)
            return f"{base_name}[{inner}]"
        return base_name

    if hasattr(annotation, "__pydantic_generic_metadata__"):
        origin_cls = getattr(annotation, "__origin__", None) or annotation
        if isinstance(origin_cls, type) and issubclass(origin_cls, BaseModel):
            base_name = model_title(origin_cls)
            args = get_args(annotation)
            if args:
                inner = ", ".join(type_label(a) for a in args)
                return f"{base_name}[{inner}]"
            return base_name

    if isinstance(annotation, type):
        if issubclass(annotation, BaseModel):
            return model_title(annotation)
        if issubclass(annotation, Enum):
            return _enum_label(annotation)
        if annotation in _FRIENDLY:
            return _FRIENDLY[annotation]
        return annotation.__name__

    return strip_module_paths(str(annotation))


def field_type_label(field: FieldInfo) -> str:
    return type_label(field.annotation)


def format_default(fi: FieldInfo) -> str:
    """Return the default value as plain text. Formatting is handled by the renderer."""
    if fi.default is None or fi.default is PydanticUndefined:
        return "—"
    d = fi.default
    if isinstance(d, Enum):
        return str(d.value)
    return str(d)
