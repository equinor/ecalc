from abc import ABC, abstractmethod
from typing import Self, override
from uuid import UUID


class Entity[TId: UUID](ABC):
    """
    Base class for all DDD Entities.
    All entities must have their own ID, which is of type UUID
    This is to make it "type safe" to use correct ID for correct entity,
    and to make the code clearer.

    Subclasses must annotate their ID field as `Final` to signal immutability
    to the type checker, e.g.:

        self._id: Final[DummyId] = dummy_id or DummyEntity._create_id()
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

        TODO: Should we really make it private with __create_id(..)?
        Returns:

        """
        ...

    @override
    def __eq__(self, other: object) -> bool:
        """
        An entity's identity is defined by the ID, thus equality comparison
        with another entity is by comparing the ID. However, we want to handle
        the special cases for None explicitly, and fail if we compare
        with a non-entity, which should be a programming error ...

        Also, we want to make sure that we only compare entities of the same type,
        otherwise we might have two different entities with the same ID,
        which should not be considered equal.

        We might change that later, but it makes sense for now.
        Args:
            other:

        Returns: True if same ID and same type, False otherwise

        """
        if other is None:
            return False
        if not isinstance(other, Entity):
            raise TypeError(
                f"Cannot compare Entity with {type(other).__name__}. "
                "Entities can only be compared with other Entities."
            )
        return type(self) is type(other) and self.get_id() == other.get_id()

    @override
    def __hash__(self) -> int:
        """
        Once an ID is set, it cannot change (by definition). It should
        therefore be safe to hash it a
        Returns:

        """
        return hash(self.get_id())
