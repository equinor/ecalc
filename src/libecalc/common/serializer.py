from libecalc.common.datetime.utils import DateUtils


class Serializer:
    @staticmethod
    def to_dict(obj, seen=None) -> dict:
        if seen is None:
            seen = set()

        if id(obj) in seen:
            return {"__circular_reference__": True}

        seen.add(id(obj))

        if hasattr(obj, "__dict__"):
            result = {}
            for key, value in vars(obj).items():
                if hasattr(value, "__dict__"):
                    result[key] = Serializer.to_dict(value, seen)
                elif isinstance(value, list):
                    result[key] = [
                        Serializer.to_dict(item, seen) if hasattr(item, "__dict__") else DateUtils.serialize(item)
                        for item in value
                    ]
                else:
                    result[key] = DateUtils.serialize(value)
            return result
        else:
            raise TypeError(f"Object of type {type(obj)} is not serializable")

    @staticmethod
    def from_dict(cls, data: dict):
        return cls(**data)
