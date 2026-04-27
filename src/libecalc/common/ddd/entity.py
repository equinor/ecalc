from abc import ABC, abstractmethod
from typing import Self
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

    @classmethod
    @abstractmethod
    def _create_id(cls: type[Self]) -> TId:
        """
        Enforce a common way to generate ID, and "force" it to be done within
        the class and encapsulation itself, to avoid breaking the rule of responsibility

        Because a static method does not have access to the type parameter TId, it must be
        a class method. Therefore it must also be accessed via lambda in field declaration to
        defer evaluation until the class is fully defined.
        Returns:

        """
        ...
