"""Extract expression variable references from pydantic models.

Recursively walks a pydantic BaseModel instance and finds all fields
annotated as YamlExpressionType (detected by the ``EXPRESSION_MARKER``
sentinel in the Annotated metadata). For each expression value found,
the reference tokens (time-series names, ``$var.*`` references, etc.) are
collected.
"""

from __future__ import annotations

import types
import typing
from typing import Any

from pydantic import BaseModel

from libecalc.expression.expression import Expression, ExpressionType
from libecalc.presentation.yaml.yaml_types.components.yaml_expression_type import EXPRESSION_MARKER


def _is_expression_type(annotation: Any) -> bool:
    """Return True if *annotation* is ``Annotated[..., EXPRESSION_MARKER, ...]``."""
    if typing.get_origin(annotation) is typing.Annotated:
        return any(m is EXPRESSION_MARKER for m in typing.get_args(annotation)[1:])
    return False


def _contains_expression_type(annotation: Any) -> bool:
    """Return True if *annotation* is, or contains, a YamlExpressionType.

    Recursively checks all type arguments of any parameterized generic
    (Union, list, dict, tuple, set, Annotated, etc.).
    """
    if _is_expression_type(annotation):
        return True

    args = typing.get_args(annotation)
    if not args:
        return False

    return any(_contains_expression_type(arg) for arg in args)


def _is_pydantic_model(annotation: Any) -> bool:
    """Return True if *annotation* is a concrete BaseModel subclass."""
    return isinstance(annotation, type) and issubclass(annotation, BaseModel)


def _unwrap_to_model_types(annotation: Any) -> list[type[BaseModel]]:
    """Return all BaseModel subclasses reachable from *annotation* (unwrapping Union/list/Annotated)."""
    if _is_pydantic_model(annotation):
        return [annotation]

    origin = typing.get_origin(annotation)
    if origin is typing.Union or isinstance(annotation, types.UnionType):
        result: list[type[BaseModel]] = []
        for arg in typing.get_args(annotation):
            result.extend(_unwrap_to_model_types(arg))
        return result

    if origin is list:
        args = typing.get_args(annotation)
        return _unwrap_to_model_types(args[0]) if args else []

    if origin is typing.Annotated:
        return _unwrap_to_model_types(typing.get_args(annotation)[0])

    if origin is dict:
        args = typing.get_args(annotation)
        result = []
        for arg in args:
            result.extend(_unwrap_to_model_types(arg))
        return result

    return []


def _has_expression_marker(metadata: list[Any]) -> bool:
    """Return True if *metadata* contains the ``EXPRESSION_MARKER`` sentinel."""
    return any(m is EXPRESSION_MARKER for m in metadata)


def _collect_expression_values(model: BaseModel) -> list[ExpressionType]:
    """Recursively collect all expression-typed field values from *model*."""
    values: list[ExpressionType] = []

    for field_name, field_info in type(model).model_fields.items():
        field_value = getattr(model, field_name, None)
        if field_value is None:
            continue

        annotation = field_info.annotation
        is_expression = _has_expression_marker(field_info.metadata) or _contains_expression_type(annotation)

        if is_expression:
            # The value is either a single expression or a list of expressions
            if isinstance(field_value, list):
                for item in field_value:
                    if isinstance(item, (str, int, float)):
                        values.append(item)
                    elif isinstance(item, BaseModel):
                        values.extend(_collect_expression_values(item))
            elif isinstance(field_value, dict):
                for v in field_value.values():
                    if isinstance(v, (str, int, float)):
                        values.append(v)
                    elif isinstance(v, BaseModel):
                        values.extend(_collect_expression_values(v))
                    elif isinstance(v, list):
                        for item in v:
                            if isinstance(item, (str, int, float)):
                                values.append(item)
                            elif isinstance(item, BaseModel):
                                values.extend(_collect_expression_values(item))
            elif isinstance(field_value, (str, int, float)):
                values.append(field_value)
        else:
            # Recurse into nested pydantic models
            model_types = _unwrap_to_model_types(annotation)
            if model_types:
                if isinstance(field_value, BaseModel):
                    values.extend(_collect_expression_values(field_value))
                elif isinstance(field_value, list):
                    for item in field_value:
                        if isinstance(item, BaseModel):
                            values.extend(_collect_expression_values(item))
                elif isinstance(field_value, dict):
                    for v in field_value.values():
                        if isinstance(v, BaseModel):
                            values.extend(_collect_expression_values(v))
                        elif isinstance(v, list):
                            for item in v:
                                if isinstance(item, BaseModel):
                                    values.extend(_collect_expression_values(item))

    return values


def extract_expression_references(model: BaseModel) -> set[str]:
    """Return all variable references used in expressions within *model*.

    Recursively inspects a pydantic BaseModel for fields annotated as
    ``YamlExpressionType`` and extracts the reference tokens (time-series
    names, ``$var.*`` variables, etc.) from each expression.

    Args:
        model: Any pydantic BaseModel instance (e.g. ``YamlProcessSimulation``).

    Returns:
        A set of variable reference strings (e.g.
        ``{"SIM1;OIL_PROD", "$var.regularity"}``).
    """
    expression_values = _collect_expression_values(model)
    references: set[str] = set()
    for expr_value in expression_values:
        expression = Expression.setup_from_expression(expr_value)
        references.update(expression.variables)
    return references
