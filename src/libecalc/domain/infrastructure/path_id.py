from __future__ import annotations

import uuid


def _generate_id(*args: str) -> str:
    """
    Generate an id from one or more strings. The string is encoded to avoid it being used to get other info than
    the id, i.e. it should not be used to get the name of a consumer, even if the name might be used to create the id.

    If there are many strings they are joined together.
    """
    return "-".join(args)


def _generate_uuid_from_string(value: str) -> uuid.UUID:
    """Generate a UUID from a string"""
    return uuid.uuid5(uuid.NAMESPACE_DNS, value)


def _generate_uuid(*args: str) -> uuid.UUID:
    return _generate_uuid_from_string(_generate_id(*args))


class PathID:
    """
    An ID used by entities.
    Some entities have unique names, others need a path to be unique.
    This class keeps track of that and can provide model unique ids, model unique tuple and the name of the entity with the id.
    """

    def __init__(self, name: str, parent: PathID | None = None):
        self._name = name
        self._parent = parent

    def get_name(self) -> str:
        return self._name

    def get_parent(self) -> PathID | None:
        return self._parent

    def get_model_unique_id(self) -> uuid.UUID:
        return _generate_uuid(*self.get_unique_tuple_str())

    def has_unique_name(self) -> bool:
        return self._parent is None

    def get_unique_tuple_str(self) -> tuple[str, ...]:
        if self.has_unique_name():
            return (self._name,)

        return (self._name, *self._parent.get_unique_tuple_str())
