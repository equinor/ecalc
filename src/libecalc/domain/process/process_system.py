from __future__ import annotations

import abc
from typing import Protocol, TypeVar
from uuid import UUID

ProcessUnitID = UUID


class Stream(Protocol):
    from_process_unit_id: ProcessUnitID | None
    to_process_unit_id: ProcessUnitID | None


class MultiPhaseStream(Stream):
    """
    Represents a fluid stream with multiple phases, liquid and gas.

    """

    ...


class LiquidStream(Stream):
    """
    Represents a fluid stream with only a liquid phase.
    """

    ...


TStream = TypeVar("TStream", bound=LiquidStream | MultiPhaseStream)


class ProcessUnit(abc.ABC):
    @abc.abstractmethod
    def get_id(self) -> ProcessUnitID: ...

    @abc.abstractmethod
    def get_type(self) -> str: ...

    @abc.abstractmethod
    def get_name(self) -> str: ...

    @abc.abstractmethod
    def get_streams(self) -> list[LiquidStream] | list[MultiPhaseStream]: ...


class ProcessSystem(ProcessUnit, abc.ABC):
    @abc.abstractmethod
    def get_process_units(self) -> list[ProcessSystem | ProcessUnit]: ...
