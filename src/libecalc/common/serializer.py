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
                        Serializer.to_dict(item, seen) if hasattr(item, "__dict__") else item for item in value
                    ]
                elif isinstance(value, dict):
                    result[key] = {
                        k: Serializer.to_dict(v, seen) if hasattr(v, "__dict__") else v for k, v in value.items()
                    }
                else:
                    result[key] = Serializer.serialize_value(value)
            return result
        else:
            return Serializer.serialize_value(obj)  # Directly serialize simple values

    @staticmethod
    def serialize_value(value):
        if isinstance(value, (int | float | str | bool)):
            return value
        elif DateUtils.is_date(value):
            return DateUtils.serialize(value)
        else:
            return str(value)  # Fallback for other types

    @staticmethod
    def from_dict(cls, data: dict):
        return cls(**data)
