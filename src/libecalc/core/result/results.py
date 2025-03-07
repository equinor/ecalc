from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Annotated, Any, Literal, Self, Union

from pydantic import Field

from libecalc.common.component_type import ComponentType
from libecalc.common.time_utils import Periods
from libecalc.common.utils.rates import (
    TimeSeriesBoolean,
    TimeSeriesFloat,
    TimeSeriesInt,
    TimeSeriesStreamDayRate,
)
from libecalc.core.result.base import EcalcResultBaseModel
from libecalc.domain.process.core.results import CompressorStreamCondition, TurbineResult
from libecalc.domain.process.core.results.compressor import (
    CompressorStageResult,
    CompressorTrainCommonShaftFailureStatus,
)


class CommonResultBase(EcalcResultBaseModel):
    """Base component for all results: Model, Installation, GenSet, Consumer System, Consumer, etc."""

    periods: Periods
    is_valid: TimeSeriesBoolean

    # We need both energy usage and power rate since we sometimes want both fuel and power usage.
    energy_usage: TimeSeriesStreamDayRate
    power: TimeSeriesStreamDayRate | None


class GenericComponentResult(CommonResultBase):
    typ: Literal["generc"] = "generc"
    id: str


class GeneratorSetResult(GenericComponentResult):
    """The Generator set result component."""

    typ: Literal["genset"] = "genset"
    power_capacity_margin: TimeSeriesStreamDayRate


class ConsumerSystemResult(GenericComponentResult):
    typ: Literal["system"] = "system"
    operational_settings_used: TimeSeriesInt
    operational_settings_results: dict[int, list[Any]] | None


class CompressorResult(GenericComponentResult):
    typ: Literal["comp"] = "comp"
    recirculation_loss: TimeSeriesStreamDayRate
    rate_exceeds_maximum: TimeSeriesBoolean

    def get_subset(self, indices: list[int]) -> Self:
        return self.__class__(
            id=self.id,
            periods=Periods([self.periods.periods[index] for index in indices]),
            energy_usage=self.energy_usage[indices],
            is_valid=self.is_valid[indices],
            power=self.power[indices] if self.power is not None else None,
            recirculation_loss=self.recirculation_loss[indices],
            rate_exceeds_maximum=self.rate_exceeds_maximum[indices],
        )


class PumpResult(GenericComponentResult):
    typ: Literal["pmp"] = "pmp"
    inlet_liquid_rate_m3_per_day: TimeSeriesStreamDayRate
    inlet_pressure_bar: TimeSeriesFloat
    outlet_pressure_bar: TimeSeriesFloat
    operational_head: TimeSeriesFloat

    def get_subset(self, indices: list[int]) -> Self:
        return self.__class__(
            id=self.id,
            periods=Periods([self.periods.periods[index] for index in indices]),
            energy_usage=self.energy_usage[indices],
            is_valid=self.is_valid[indices],
            power=self.power[indices] if self.power is not None else None,
            inlet_liquid_rate_m3_per_day=self.inlet_liquid_rate_m3_per_day[indices],
            inlet_pressure_bar=self.inlet_pressure_bar[indices],
            outlet_pressure_bar=self.outlet_pressure_bar[indices],
            operational_head=self.operational_head[indices],
        )


class ConsumerModelResultBase(ABC, CommonResultBase):
    """The Consumer base result component."""

    @property
    @abstractmethod
    def component_type(self): ...

    name: str


class PumpModelResult(ConsumerModelResultBase):
    """The Pump result component."""

    inlet_liquid_rate_m3_per_day: list[float | None]
    inlet_pressure_bar: list[float | None]
    outlet_pressure_bar: list[float | None]
    operational_head: list[float | None]

    @property
    def component_type(self):
        return ComponentType.PUMP


class CompressorModelResult(ConsumerModelResultBase):
    rate_sm3_day: list[float | None] | list[list[float | None]]
    max_standard_rate: list[float | None] | list[list[float | None]] | None = None

    stage_results: list[CompressorStageResult]
    failure_status: list[CompressorTrainCommonShaftFailureStatus | None]
    turbine_result: TurbineResult | None = None

    inlet_stream_condition: CompressorStreamCondition
    outlet_stream_condition: CompressorStreamCondition

    @property
    def component_type(self):
        return ComponentType.COMPRESSOR


class GenericModelResult(ConsumerModelResultBase):
    """Generic consumer result component."""

    @property
    def component_type(self):
        return ComponentType.GENERIC


# Consumer model result is referred to as ENERGY_USAGE_MODEL in the input YAML
ConsumerModelResult = Union[CompressorModelResult, PumpModelResult, GenericModelResult]

ComponentResult = Annotated[
    Union[
        GeneratorSetResult,
        ConsumerSystemResult,
        CompressorResult,
        PumpResult,
        GenericComponentResult,
    ],
    Field(discriminator="typ"),
]  # Order is important as pydantic will parse results, so any result will be converted to the first fit in this list.


class EcalcModelResult(EcalcResultBaseModel):
    """Result object holding one component for each part of the eCalc model run."""

    component_result: ComponentResult
    sub_components: list[ComponentResult]
    models: list[ConsumerModelResult]
