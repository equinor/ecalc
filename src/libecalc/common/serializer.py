# libecalc/src/libecalc/common/serializer.py

from libecalc.common.datetime.utils import DateUtils


class Serializer:
    @staticmethod
    def to_dict(obj, seen=None) -> dict:
        if seen is None:
            seen = set()

        if id(obj) in seen:
            return None  # Skip circular references

        seen.add(id(obj))

        if hasattr(obj, "__dict__"):
            result = {}
            for key, value in vars(obj).items():
                if key.startswith("_"):
                    continue  # Skip private attributes
                if hasattr(value, "__dict__"):
                    serialized_value = Serializer.to_dict(value, seen)
                    if serialized_value is not None:
                        result[key] = serialized_value
                elif isinstance(value, list):
                    result[key] = [
                        Serializer.to_dict(item, seen) if hasattr(item, "__dict__") else DateUtils.serialize(item)
                        for item in value
                    ]
                elif isinstance(value, dict):
                    result[key] = {
                        k: Serializer.to_dict(v, seen) if hasattr(v, "__dict__") else DateUtils.serialize(v)
                        for k, v in value.items()
                    }
                else:
                    result[key] = DateUtils.serialize(value)
            return result
        else:
            return DateUtils.serialize(obj)  # Directly serialize simple values

    @staticmethod
    def from_dict(cls, data: dict):
        return cls(**data)
