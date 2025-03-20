# libecalc/src/libecalc/common/serializer.py

import json
from enum import Enum
from typing import Any

from libecalc.common.datetime.utils import DateUtils


class Serializer:
    @staticmethod
    def to_dict(obj, ref_map=None) -> dict:
        if ref_map is None:
            ref_map = {}

        obj_id = id(obj)
        if obj_id in ref_map:
            return ref_map[obj_id]  # Return the reference to handle circular references

        if isinstance(obj, Enum):
            return obj.value  # Serialize Enum types by their value

        if hasattr(obj, "__dict__"):
            result: dict[str, Any] = {}
            ref_map[obj_id] = result  # Add the object to the reference map
            for key, value in vars(obj).items():
                if key.startswith("_"):
                    continue  # Skip private attributes
                if hasattr(value, "__dict__"):
                    result[key] = Serializer.to_dict(value, ref_map)
                elif isinstance(value, list):
                    result[key] = [
                        Serializer.to_dict(item, ref_map) if hasattr(item, "__dict__") else item for item in value
                    ]
                elif isinstance(value, dict):
                    result[key] = {
                        k: Serializer.to_dict(v, ref_map) if hasattr(v, "__dict__") else v for k, v in value.items()
                    }
                else:
                    result[key] = Serializer.serialize_value(value)
            # Include class variables
            for key, _value in obj.__class__.__annotations__.items():
                result[str(key)] = getattr(obj, key, None)
            return result
        else:
            return Serializer.serialize_value(obj)  # Directly serialize simple values

    @staticmethod
    def serialize_value(value):
        if isinstance(value, (int | float | str | bool)):
            return value
        elif DateUtils.is_date(value):
            return DateUtils.serialize(value)
        elif isinstance(value, Enum):  # Check if the value is of type Enum
            return value.value  # Serialize Enum types by their value
        elif value is None:
            return None  # Serialize None as null
        else:
            return str(value)  # Fallback for other types

    @staticmethod
    def from_dict(cls, data: dict):
        return cls(**data)

    @staticmethod
    def to_json(obj) -> str:
        return json.dumps(Serializer.to_dict(obj), default=str)
