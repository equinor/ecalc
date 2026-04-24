from abc import ABC, abstractmethod
from uuid import UUID


class Entity[TId: UUID](ABC):
    """
    Base class for all DDD Entities.
    All entities must have their own ID, which is of type UUID
    This is to make it "type safe" to use correct ID for correct entity,
    and to make the code clearer
    """

    @abstractmethod
    def get_id(self) -> TId: ...

    @abstractmethod
    @staticmethod
    def _create_id() -> TId: ...
