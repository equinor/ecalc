from collections.abc import Sequence
from dataclasses import dataclass
from typing import Self

from libecalc.common.time_utils import Period
from libecalc.common.units import Unit
from libecalc.common.utils.rates import TimeSeriesFloat, TimeSeriesRate
from libecalc.domain.process.process_system import (
    LiquidStream,
    MultiPhaseStream,
    Pressure,
    ProcessEntityID,
    ProcessUnitStreams,
    Rate,
)


@dataclass
class EcalcModelResultRate(Rate):
    periods: list[Period]
    values: list[float]
    unit: Unit

    @classmethod
    def from_time_series(cls, time_series: TimeSeriesFloat | TimeSeriesRate) -> Self:
        return cls(
            values=time_series.values,
            periods=time_series.periods.periods,
            unit=time_series.unit,
        )


@dataclass
class EcalcModelResultPressure(Pressure):
    periods: list[Period]
    values: list[float]
    unit: Unit

    @classmethod
    def from_time_series(cls, time_series: TimeSeriesFloat) -> Self:
        return cls(
            values=time_series.values,
            periods=time_series.periods.periods,
            unit=time_series.unit,
        )


@dataclass(frozen=True)
class EcalcModelResultMultiPhaseStream(MultiPhaseStream):
    from_process_unit_id: ProcessEntityID | None
    to_process_unit_id: ProcessEntityID | None
    rate: EcalcModelResultRate
    pressure: EcalcModelResultPressure


@dataclass(frozen=True)
class EcalcModelResultLiquidStream(LiquidStream):
    from_process_unit_id: ProcessEntityID | None
    to_process_unit_id: ProcessEntityID | None
    rate: EcalcModelResultRate | None
    pressure: EcalcModelResultPressure | None


@dataclass(frozen=True)
class EcalcProcessUnitStreams(ProcessUnitStreams):
    inlet_streams: Sequence[LiquidStream] | Sequence[MultiPhaseStream]
    outlet_streams: Sequence[LiquidStream] | Sequence[MultiPhaseStream]
