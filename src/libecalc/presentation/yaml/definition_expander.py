"""
Generic definition expander for YAML models.

Walks a pydantic BaseModel recursively and replaces DefinitionReference strings
with the actual definition objects from a provided definitions registry.
"""

from __future__ import annotations

import types
from collections.abc import Mapping, Sequence, Set
from typing import Annotated, Any, Union, get_args, get_origin

from pydantic import BaseModel

from libecalc.presentation.yaml.yaml_types.process.yaml_process_references import DefinitionReference


class DefinitionReferenceError(Exception):
    """Base error for definition reference resolution failures."""

    def __init__(self, reference: str, message: str):
        self.reference = reference
        super().__init__(message)


class DefinitionNotFoundError(DefinitionReferenceError):
    """Raised when a DefinitionReference string does not match any known definition."""

    def __init__(self, reference: str, available: list[str]):
        self.available = available
        super().__init__(
            reference=reference,
            message=f"Definition reference '{reference}' not found. Available definitions: {available}",
        )


class DefinitionTypeError(DefinitionReferenceError):
    """Raised when a resolved definition does not match the expected type."""

    def __init__(self, reference: str, actual_type: type, expected_types: list[type]):
        self.actual_type = actual_type
        self.expected_types = expected_types
        expected_names = [t.__name__ for t in expected_types]
        actual_name = actual_type.__name__
        super().__init__(
            reference=reference,
            message=(
                f"Definition reference '{reference}' resolved to type '{actual_name}', "
                f"but expected one of: {', '.join(expected_names)}"
            ),
        )


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
        resolved = _lookup_definition(value, definitions)
        _validate_resolved_type(value, resolved, annotation)
        return resolved

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
        raise DefinitionNotFoundError(reference=reference, available=list(definitions.keys()))
    return definitions[reference]


def _validate_resolved_type(reference: str, resolved: Any, annotation: Any) -> None:
    """Validate that a resolved definition matches the expected types in the union annotation.

    For a field typed as ``SomeModel | DefinitionReference``, the resolved object must be
    an instance of ``SomeModel`` (or any of the other non-DefinitionReference types in the union).

    Raises:
        DefinitionTypeError: If the resolved object does not match any expected type.
    """
    expected_types = get_expected_types(annotation)

    if not expected_types:
        return  # No concrete types to validate against

    if not isinstance(resolved, tuple(expected_types)):
        raise DefinitionTypeError(
            reference=reference,
            actual_type=type(resolved),
            expected_types=expected_types,
        )


def get_expected_types(annotation: Any) -> list[type]:
    """Extract the concrete types from a union annotation, excluding DefinitionReference.

    Handles plain unions (``A | B | DefinitionReference``) as well as
    ``Annotated[Union[...], ...]`` wrappers used by pydantic discriminated unions.

    Returns:
        A list of concrete types that a resolved definition must be an instance of.
    """
    args = get_args(annotation)
    expected: list[type] = []
    for a in args:
        if a is DefinitionReference:
            continue
        # Unwrap Annotated[Union[...], ...] (e.g. discriminated unions)
        if get_origin(a) is Annotated:
            inner_args = get_args(a)
            inner = inner_args[0] if inner_args else a
            inner_origin = get_origin(inner)
            if inner_origin is Union or isinstance(inner, types.UnionType):
                for t in get_args(inner):
                    if isinstance(t, type):
                        expected.append(t)
                continue
        if isinstance(a, type):
            expected.append(a)
    return expected
