import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any, TypeVar

import numpy as np
import pandas as pd
from pydantic import BaseModel

from libecalc.common.logger import logger

from .constants import CIRCULAR
from .datetime_utils import DateTimeUtils
from .helpers import (
    serialize_dataframe,
    serialize_dict,
    serialize_dict_like,
    serialize_iterable,
    serialize_list,
    serialize_slots,
)
from .tracking import is_trackable_object
from .types import JSONSerializable

T = TypeVar("T")


class Serializer:
    """
    Utility class for serializing Python objects to dictionaries and JSON.

    Handles a wide range of data types including:
    - Primitive types: int, float, str, bool, None
    - Enum values
    - Lists, sets, and tuples
    - Dictionaries
    - Dataclasses
    - Numpy scalars and arrays
    - Pandas Series and DataFrames
    - Pydantic models
    - Custom objects with __dict__ or __slots__
    - Date and datetime objects

    Circular references are detected and excluded from the output.
    """

    @staticmethod
    def to_dict(obj: Any, _seen: set[int] | None = None) -> JSONSerializable:
        """
        Convert a supported Python object into a JSON-serializable structure.

        This method handles most object types (dataclasses, pydantic models, enums, etc.),
        and detects circular references using a `_seen` set.

        Used as the primary entry point for converting objects to dict-like data.
        """

        if _seen is None:
            _seen = set()

        # Track circular references if needed
        if is_trackable_object(obj):
            obj_id = id(obj)
            if obj_id in _seen:
                return CIRCULAR
            _seen.add(obj_id)

        # Handle Pydantic models
        if isinstance(obj, BaseModel):
            return Serializer.to_dict(obj.model_dump())

        # Enum (serialize as value)
        if isinstance(obj, Enum):
            return obj.value

        # Pandas Series → dict
        if isinstance(obj, pd.Series):
            return obj.to_dict()

        # Dataclasses → dict
        if is_dataclass(obj):
            return Serializer.to_dict(asdict(obj), _seen)

        # Regular objects with __dict__
        if hasattr(obj, "__dict__"):
            return serialize_dict_like(vars(obj), obj, Serializer.to_dict, _seen)

        # Objects using __slots__
        if hasattr(obj, "__slots__"):
            return serialize_slots(obj, Serializer.to_dict, _seen)

        # Fallback to generic value serialization
        return Serializer.serialize_value(obj, _seen)

    @staticmethod
    def serialize_value(value: Any, _seen: set[int] | None = None) -> JSONSerializable:
        """
        Fallback serializer for values not directly handled by `to_dict`.

        Used when an object is not a class with attributes, but still needs
        to be converted into a JSON-compatible value (e.g. lists, dicts,
        pandas/numpy types, or deeply nested structures).

        Still respects circular reference detection via `_seen`.
        """

        if _seen is None:
            _seen = set()

        # Primitive types
        if isinstance(value, (int | float | str | bool)):
            return value

        # Date/time
        if DateTimeUtils.is_date(value):
            return DateTimeUtils.serialize_date(value)

        # Enum (re-check)
        if isinstance(value, Enum):
            return value.value

        if value is None:
            return None

        # lists
        if isinstance(value, list):
            return serialize_list(value, Serializer.to_dict, _seen)

        # dictionaries
        if isinstance(value, dict):
            return serialize_dict(value, Serializer.to_dict, _seen)

        # Pandas DataFrame → list of records
        if isinstance(value, pd.DataFrame):
            return serialize_dataframe(value, Serializer.to_dict, _seen)

        # Set / tuple → list
        if isinstance(value, (set | tuple)):
            return serialize_iterable(value, Serializer.to_dict, _seen)

        # NumPy scalar
        if isinstance(value, np.generic):
            return value.item()

        # NumPy array
        if isinstance(value, np.ndarray):
            return value.tolist()

        # Fallback for objects with __dict__ or __slots__
        if hasattr(value, "__dict__") or hasattr(value, "__slots__"):
            serialized = Serializer.to_dict(value, _seen)
            if serialized is not CIRCULAR and serialized is not None:
                # If empty dict, fallback to string
                if isinstance(serialized, dict) and not serialized:
                    return str(value)
                return serialized
            return str(value)

        # Unknown type – fallback to str
        logger.warning(f"Unhandled type {type(value)}, defaulting to string.")
        return str(value)

    @staticmethod
    def from_dict(cls: type[T], data: dict[str, Any]) -> T:
        # Deserializes a dict back to an object (if safe)
        if data is None:
            raise ValueError(f"Cannot deserialize object of type {cls} from None")
        return cls(**data)

    @staticmethod
    def to_json(obj: Any) -> str:
        # Converts any object to JSON string
        result = Serializer.to_dict(obj)
        return json.dumps(result or {})
