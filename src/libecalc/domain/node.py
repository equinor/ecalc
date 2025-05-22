import abc
from typing import TypeAlias
from uuid import UUID

PhysicalID: TypeAlias = UUID


class PhysicalUnit(abc.ABC):
    @abc.abstractmethod
    def get_unit_id(self) -> UUID: ...

    @abc.abstractmethod
    def get_model_unique_id(self) -> UUID: ...

    @abc.abstractmethod
    def get_name(self) -> str: ...


class Node(abc.ABC):
    @abc.abstractmethod
    def get_physical_unit(self) -> PhysicalUnit: ...
