import json
from enum import Enum
from typing import Any

from libecalc.common.datetime.utils import DateUtils


class Serializer:
    @staticmethod
    def to_dict(obj: Any, ref_map: dict[int, Any] = None) -> dict[str, Any]:
        if ref_map is None:
            ref_map = {}

        obj_id = id(obj)
        if obj_id in ref_map:
            return ref_map[obj_id]  # Return the reference to handle circular references

        if isinstance(obj, Enum):
            return obj.value  # Serialize Enum types by their value

        if hasattr(obj, "to_dict"):
            return obj.to_dict()  # Use the custom to_dict method if available

        if hasattr(obj, "__dict__"):
            result: dict[str, Any] = {}
            ref_map[obj_id] = result  # Add the object to the reference map
            for key, value in vars(obj).items():
                if key.startswith("_"):
                    continue  # Skip private attributes
                result[key] = (
                    Serializer.to_dict(value, ref_map)
                    if hasattr(value, "__dict__")
                    else Serializer.serialize_value(value)
                )

            # Include class variables
            # for key, _value in obj.__class__.__annotations__.items():
            #     result[str(key)] = getattr(obj, key, None)

            return result
        else:
            return Serializer.serialize_value(obj)  # Directly serialize simple values

    @staticmethod
    def serialize_value(value: Any) -> Any:
        if isinstance(value, (int | float | str | bool)):
            return value
        elif DateUtils.is_date(value):
            return DateUtils.serialize(value)
        elif isinstance(value, Enum):  # Check if the value is of type Enum
            return value.value  # Serialize Enum types by their value
        elif value is None:
            return None  # Serialize None as null
        elif isinstance(value, list):
            return [
                Serializer.to_dict(v) if hasattr(v, "__dict__") else Serializer.serialize_value(v) for v in value
            ]  # Serialize list elements
        elif isinstance(value, dict):
            return {
                k: Serializer.to_dict(v) if hasattr(v, "__dict__") else Serializer.serialize_value(v)
                for k, v in value.items()
            }  # Serialize dict elements
        elif hasattr(value, "__dict__"):
            return Serializer.to_dict(value)  # Serialize objects without to_dict method
        else:
            return str(value)  # Fallback for other types

    @staticmethod
    def from_dict(cls: Any, data: dict[str, Any]) -> Any:
        return cls(**data)

    @staticmethod
    def to_json(obj: Any) -> str:
        return json.dumps(Serializer.to_dict(obj), default=str)
