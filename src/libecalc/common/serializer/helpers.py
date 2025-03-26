from typing import Any

import pandas as pd

from .constants import CIRCULAR

"""
Helper functions for the Serializer module.

These functions handle the serialization of internal structures such as:
- Objects with __dict__ or __slots__
- Lists, dictionaries, sets, tuples
- Pandas DataFrames

Each function is designed to work recursively and skip circular references.
Circular objects are detected by the Serializer and marked with a special
sentinel value (`CIRCULAR`), which is then excluded from the output.
"""


def serialize_dict_like(attrs: dict[str, Any], obj: Any, to_dict_fn, _seen: set[int]) -> dict:
    """Serialize a dictionary-like object (e.g., from __dict__) while skipping circular references."""
    result = {}
    for key, value in attrs.items():
        if key.startswith("_"):
            continue
        serialized_value = to_dict_fn(value, _seen)
        if serialized_value is not CIRCULAR:
            result[key] = serialized_value
    if "typ" in obj.__class__.__annotations__:
        result["typ"] = getattr(obj, "typ", None)
    return result


def serialize_slots(obj: Any, to_dict_fn, _seen: set[int]) -> dict:
    """Serialize an object that defines __slots__, skipping circular references."""
    result = {}
    for slot in getattr(obj, "__slots__", []):
        if hasattr(obj, slot):
            serialized_value = to_dict_fn(getattr(obj, slot), _seen)
            if serialized_value is not CIRCULAR:
                result[slot] = serialized_value
    return result


def serialize_list(value: list, to_dict_fn, _seen: set[int]) -> list:
    """Serialize a list of values using the given to_dict function."""
    return [serialized for item in value if (serialized := to_dict_fn(item, _seen)) is not CIRCULAR]


def serialize_dict(value: dict, to_dict_fn, _seen: set[int]) -> dict:
    """Serialize a dictionary with string keys and serializable values."""
    return {str(k): v for k, v in ((k, to_dict_fn(val, _seen)) for k, val in value.items()) if v is not CIRCULAR}


def serialize_dataframe(df: pd.DataFrame, to_dict_fn, _seen: set[int]) -> list[dict]:
    """Serialize a pandas DataFrame as a list of row dictionaries."""
    return [to_dict_fn(row, _seen) for row in df.to_dict(orient="records")]


def serialize_iterable(value: Any, to_dict_fn, _seen: set[int]) -> list:
    """Serialize any iterable (e.g. set, tuple) by converting items to serializable form."""
    return [serialized for item in value if (serialized := to_dict_fn(item, _seen)) is not CIRCULAR]
