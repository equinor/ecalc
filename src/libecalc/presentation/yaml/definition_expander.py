"""
Generic definition expander for YAML models.

Walks a pydantic BaseModel recursively and replaces DefinitionReference strings
with the actual definition objects from a provided definitions registry.
"""

from __future__ import annotations

import types
from collections.abc import Mapping, Sequence, Set
from typing import Any, Union, get_args, get_origin

from pydantic import BaseModel

from libecalc.presentation.yaml.yaml_types.process.yaml_process_references import DefinitionReference


def expand_definitions[T: BaseModel](model: T, definitions: dict[str, Any]) -> T:
    """Expand all DefinitionReference strings in a pydantic model tree.

    Recursively walks the model and for any field typed as `T | DefinitionReference`,
    if the value is a string, looks it up in the definitions dict and replaces it
    with the corresponding definition object.

    Args:
        model: The root pydantic model to expand references in.
        definitions: A flat mapping of {reference_name: definition_object}.

    Returns:
        A new model instance with all DefinitionReference strings replaced by their definition objects.

    Raises:
        KeyError: If a reference string cannot be found in the definitions registry.
    """
    updates = {}
    for field_name, field_info in type(model).model_fields.items():
        value = getattr(model, field_name)
        if value is None:
            continue

        annotation = field_info.annotation
        resolved = _expand_value(value, annotation, definitions)
        if resolved is not value:
            updates[field_name] = resolved

    if updates:
        return model.model_copy(update=updates)
    return model


def _get_item_type(annotation: Any) -> Any:
    """Extract the element type from a generic container annotation.

    Handles list[X], set[X], frozenset[X], tuple[X, ...], dict[K, V] (returns V), etc.
    """
    args = get_args(annotation)
    if not args:
        return Any

    origin = get_origin(annotation)
    if origin is dict or (isinstance(origin, type) and issubclass(origin, Mapping)):
        return args[1] if len(args) >= 2 else Any

    # tuple[X, ...] → X; tuple[A, B, C] → we can't resolve per-position generically, use Any
    if origin is tuple:
        if len(args) == 2 and args[1] is Ellipsis:
            return args[0]
        return Any

    # list, set, frozenset, etc.
    return args[0]


def _expand_value(value: Any, annotation: Any, definitions: dict[str, Any]) -> Any:
    """Expand a single value based on its type annotation."""

    # Check if this field is a union containing DefinitionReference
    if _is_definition_reference_union(annotation) and isinstance(value, str):
        return _lookup_definition(value, definitions)

    # Recurse into BaseModel instances
    if isinstance(value, BaseModel):
        return expand_definitions(value, definitions)

    # Recurse into mappings (dict, OrderedDict, etc.)
    if isinstance(value, Mapping):
        item_type = _get_item_type(annotation)
        return type(value)({k: _expand_value(v, item_type, definitions) for k, v in value.items()})  # type: ignore[call-arg]

    # Recurse into sequences and sets (list, tuple, set, frozenset, etc.) but not strings
    if isinstance(value, (Sequence, Set)) and not isinstance(value, (str, bytes)):
        item_type = _get_item_type(annotation)
        return type(value)(_expand_value(item, item_type, definitions) for item in value)  # type: ignore[call-arg]

    return value


def _is_definition_reference_union(annotation: Any) -> bool:
    """Check if the annotation is a Union containing DefinitionReference."""
    origin = get_origin(annotation)
    if origin is Union or origin is types.UnionType:
        args = get_args(annotation)
        return any(a is DefinitionReference for a in args)
    return False


def _lookup_definition(reference: str, definitions: dict[str, Any]) -> Any:
    """Look up a reference string in the definitions registry."""
    if reference not in definitions:
        raise KeyError(
            f"Definition reference '{reference}' not found. Available definitions: {list(definitions.keys())}"
        )
    return definitions[reference]
