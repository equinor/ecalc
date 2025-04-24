from __future__ import annotations

import abc
from typing import Protocol
from uuid import UUID

from libecalc.common.serializable_chart import SingleSpeedChartDTO, VariableSpeedChartDTO

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


class CompressorStage(abc.ABC):
    @abc.abstractmethod
    def get_compressor_chart(self) -> VariableSpeedChartDTO | SingleSpeedChartDTO | None: ...
