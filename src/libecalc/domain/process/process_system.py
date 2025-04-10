import abc
from typing import Generic, TypeVar
from uuid import UUID

ProcessUnitID = UUID


class Stream(abc.ABC):
    @property
    @abc.abstractmethod
    def from_process_unit_id(self) -> ProcessUnitID | None: ...

    @property
    @abc.abstractmethod
    def to_process_unit_id(self) -> ProcessUnitID | None: ...


class MultiPhaseStream(Stream, abc.ABC):
    """
    Represents a fluid stream with multiple phases, liquid and gas.

    """

    ...


class LiquidStream(Stream, abc.ABC):
    """
    Represents a fluid stream with only a liquid phase.
    """

    ...


TStream = TypeVar("TStream", bound=LiquidStream | MultiPhaseStream)


class ProcessUnit(abc.ABC, Generic[TStream]):
    @abc.abstractmethod
    def get_id(self) -> ProcessUnitID: ...

    @abc.abstractmethod
    def get_type(self) -> str: ...

    @abc.abstractmethod
    def get_name(self) -> str: ...

    @abc.abstractmethod
    def get_streams(self) -> list[TStream]: ...


class ProcessSystem(ProcessUnit, abc.ABC, Generic[TStream]):
    @abc.abstractmethod
    def get_process_units(self) -> list["ProcessSystem[TStream]" | ProcessUnit[TStream]]: ...
