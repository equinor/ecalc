# libecalc/src/libecalc/common/serializer.py

from libecalc.common.datetime.utils import DateUtils
from enum import Enum

class Serializer:
    @staticmethod
    def to_dict(obj, ref_map=None) -> dict:
        if ref_map is None:
            ref_map = {}

        obj_id = id(obj)
        if obj_id in ref_map:
            return ref_map[obj_id]  # Return the reference to handle circular references

        if isinstance(obj, Enum):
            return str(obj)  # Serialize Enum types by their string representation

        if hasattr(obj, "__dict__"):
            result = {}
            ref_map[obj_id] = result  # Add the object to the reference map
            for key, value in vars(obj).items():
                if key.startswith("_"):
                    continue  # Skip private attributes
                if hasattr(value, "__dict__"):
                    result[key] = Serializer.to_dict(value, ref_map)
                elif isinstance(value, list):
                    result[key] = [
                        Serializer.to_dict(item, ref_map) if hasattr(item, "__dict__") else item
                        for item in value
                    ]
                elif isinstance(value, dict):
                    result[key] = {
                        k: Serializer.to_dict(v, ref_map) if hasattr(v, "__dict__") else v
                        for k, v in value.items()
                    }
                else:
                    result[key] = Serializer.serialize_value(value)
            return result
        else:
            return Serializer.serialize_value(obj)  # Directly serialize simple values

    @staticmethod
    def serialize_value(value):
        if isinstance(value, (int, float, str, bool)):
            return value
        elif DateUtils.is_date(value):
            return DateUtils.serialize(value)
        elif hasattr(value, "__str__"):  # Use the string representation for custom classes
            return str(value)
        else:
            return str(value)  # Fallback for other types

    @staticmethod
    def from_dict(cls, data: dict):
        return cls(**data)