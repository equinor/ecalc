import types
from typing import Any, Union, get_args

from pydantic import BaseModel

from libecalc.presentation.yaml.yaml_types.process.yaml_process_references import InstanceReference


def collect_instance_references(obj: BaseModel) -> list[str]:
    """Collect all InstanceReference string values from a BaseModel, recursively."""
    references: list[str] = []
    _collect_instance_references(obj, references)
    return references


def _annotation_contains_instance_reference(annotation: Any) -> bool:
    """Check if a type annotation involves InstanceReference."""
    if annotation is InstanceReference:
        return True
    args = get_args(annotation)
    if args:
        return any(_annotation_contains_instance_reference(a) for a in args)
    return False


def _collect_instance_references(obj: Any, references: list[str]) -> None:
    """Recursively collect all InstanceReference string values from a BaseModel."""
    if not isinstance(obj, BaseModel):
        return

    for field_name, field_info in type(obj).model_fields.items():
        annotation = field_info.annotation
        if annotation is None:
            continue
        if not _annotation_contains_instance_reference(annotation):
            continue

        value = getattr(obj, field_name, None)
        if value is None:
            continue

        _extract_references_from_value(value, annotation, references)

    # Also recurse into nested BaseModel fields that don't directly have InstanceReference
    # but may contain sub-models that do
    for field_name, field_info in type(obj).model_fields.items():
        annotation = field_info.annotation
        if annotation is None:
            continue
        if _annotation_contains_instance_reference(annotation):
            continue  # Already handled above

        value = getattr(obj, field_name, None)
        if value is None:
            continue

        if isinstance(value, BaseModel):
            _collect_instance_references(value, references)
        elif isinstance(value, list):
            for item in value:
                if isinstance(item, BaseModel):
                    _collect_instance_references(item, references)
        elif isinstance(value, dict):
            for v in value.values():
                if isinstance(v, BaseModel):
                    _collect_instance_references(v, references)


def _extract_references_from_value(value: Any, annotation: Any, references: list[str]) -> None:
    """Extract InstanceReference strings from a value based on its annotation."""
    if annotation is InstanceReference:
        if isinstance(value, str):
            references.append(value)
        return

    origin = getattr(annotation, "__origin__", None)
    args = get_args(annotation)

    # Handle union types (both X | Y syntax and typing.Union[X, Y])
    if isinstance(annotation, types.UnionType) or origin is Union:
        if isinstance(value, str):
            if any(a is InstanceReference for a in args):
                references.append(value)
        elif isinstance(value, BaseModel):
            _collect_instance_references(value, references)
        return

    if origin is list:
        if isinstance(value, list):
            for item in value:
                if isinstance(item, str) and _annotation_contains_instance_reference(args[0] if args else None):
                    references.append(item)
                elif isinstance(item, BaseModel):
                    _collect_instance_references(item, references)
    elif origin is dict:
        if isinstance(value, dict):
            key_ann = args[0] if args else None
            val_ann = args[1] if len(args) > 1 else None
            if _annotation_contains_instance_reference(key_ann):
                for k in value.keys():
                    if isinstance(k, str):
                        references.append(k)
            if val_ann and _annotation_contains_instance_reference(val_ann):
                for v in value.values():
                    _extract_references_from_value(v, val_ann, references)
            # Recurse into BaseModel values regardless
            for v in value.values():
                if isinstance(v, BaseModel):
                    _collect_instance_references(v, references)
    elif isinstance(value, BaseModel):
        _collect_instance_references(value, references)
