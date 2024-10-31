from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Annotated, Any, Literal, Optional, Self, Union

from pydantic import Field

from libecalc.common.component_type import ComponentType
from libecalc.common.stream_conditions import TimeSeriesStreamConditions
from libecalc.common.tabular_time_series import TabularTimeSeriesUtils
from libecalc.common.time_utils import Periods
from libecalc.common.utils.rates import (
    TimeSeriesBoolean,
    TimeSeriesFloat,
    TimeSeriesInt,
    TimeSeriesStreamDayRate,
)
from libecalc.core.models.results import CompressorStreamCondition, TurbineResult
from libecalc.core.models.results.compressor import (
    CompressorStageResult,
    CompressorTrainCommonShaftFailureStatus,
)
from libecalc.core.result.base import EcalcResultBaseModel


class CommonResultBase(EcalcResultBaseModel):
    """Base component for all results: Model, Installation, GenSet, Consumer System, Consumer, etc."""

    periods: Periods
    is_valid: TimeSeriesBoolean

    # We need both energy usage and power rate since we sometimes want both fuel and power usage.
    energy_usage: TimeSeriesStreamDayRate
    power: Optional[TimeSeriesStreamDayRate]


class GenericComponentResult(CommonResultBase):
    typ: Literal["generc"] = "generc"
    id: str

    def merge(self, *other_results: CompressorResult) -> Self:
        """
        Merge all attributes of TimeSeries type, while also making sure the other attributes can be merged (i.e. id should be equal).
        Args:
            *other_results:

        Returns:

        """
        # Verify that we are merging the same entity
        if len({other_result.id for other_result in other_results}) != 1:
            raise ValueError("Can not merge objects with differing ids.")

        return TabularTimeSeriesUtils.merge(self, *other_results)


class GeneratorSetResult(GenericComponentResult):
    """The Generator set result component."""

    typ: Literal["genset"] = "genset"
    power_capacity_margin: TimeSeriesStreamDayRate


class ConsumerSystemResult(GenericComponentResult):
    typ: Literal["system"] = "system"
    operational_settings_used: TimeSeriesInt
    operational_settings_results: Optional[dict[int, list[Any]]]


class CompressorResult(GenericComponentResult):
    typ: Literal["comp"] = "comp"
    recirculation_loss: TimeSeriesStreamDayRate
    rate_exceeds_maximum: TimeSeriesBoolean
    streams: Optional[list[TimeSeriesStreamConditions]] = None  # Optional because only in v2

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

    streams: Optional[list[TimeSeriesStreamConditions]] = None  # Optional because only in v2

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

    inlet_liquid_rate_m3_per_day: list[Optional[float]]
    inlet_pressure_bar: list[Optional[float]]
    outlet_pressure_bar: list[Optional[float]]
    operational_head: list[Optional[float]]

    @property
    def component_type(self):
        return ComponentType.PUMP


class CompressorModelResult(ConsumerModelResultBase):
    rate_sm3_day: Union[list[Optional[float]], list[list[Optional[float]]]]
    max_standard_rate: Optional[Union[list[Optional[float]], list[list[Optional[float]]]]] = None

    stage_results: list[CompressorStageResult]
    failure_status: list[Optional[CompressorTrainCommonShaftFailureStatus]]
    turbine_result: Optional[TurbineResult] = None

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
