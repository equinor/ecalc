from __future__ import annotations

from typing import Generic, TypeVar

from libecalc.domain.common.entity_id import ID

ID_T = TypeVar("ID_T", bound=ID)


class Entity(Generic[ID_T]):
    """DDD entity base identity only, no behaviour assumptions."""

    def __init__(self, entity_id: ID_T) -> None:
        self._id = entity_id

    def get_id(self) -> ID_T:
        return self._id

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Entity) and self.get_id().get_uuid() == other.get_id().get_uuid()

    def __hash__(self) -> int:
        return hash(self.get_id().get_uuid())
