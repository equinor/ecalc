from __future__ import annotations

import abc
from typing import Protocol
from uuid import UUID

from libecalc.common.serializable_chart import (
    SingleSpeedChartDTO,
    VariableSpeedChartDTO,
)
from libecalc.common.time_utils import Period
from libecalc.common.units import Unit

ProcessEntityID = UUID


class Rate(Protocol):
    periods: list[Period]
    values: list[float]
    unit: Unit


class Pressure(Protocol):
    periods: list[Period]
    values: list[float]
    unit: Unit


class Stream(Protocol):
    from_process_unit_id: ProcessEntityID | None
    to_process_unit_id: ProcessEntityID | None
    rate: Rate
    pressure: Pressure


class MultiPhaseStream(Stream):
    """
    A fluid stream with multiple phases, liquid and gas.

    """

    ...


class LiquidStream(Stream):
    """
    A fluid stream with only a liquid phase.
    """

    ...


class ProcessUnitStreams(Protocol):
    inlet_streams: list[MultiPhaseStream] | list[LiquidStream]
    outlet_streams: list[MultiPhaseStream] | list[LiquidStream]


class ProcessEntity(abc.ABC):
    @abc.abstractmethod
    def get_id(self) -> ProcessEntityID: ...

    @abc.abstractmethod
    def get_type(self) -> str: ...

    @abc.abstractmethod
    def get_name(self) -> str: ...


class ProcessUnit(ProcessEntity, abc.ABC):
    @abc.abstractmethod
    def get_streams(self) -> ProcessUnitStreams: ...


class ProcessSystem(ProcessEntity, abc.ABC):
    @abc.abstractmethod
    def get_process_units(self) -> list[ProcessSystem | ProcessUnit]: ...


class CompressorStage(abc.ABC):
    @abc.abstractmethod
    def get_compressor_chart(
        self,
    ) -> VariableSpeedChartDTO | SingleSpeedChartDTO | None: ...
