from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Literal, Self

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
    """
    Base component for all results: Model, Installation, GenSet, Consumer System, Consumer, etc.

    We need both energy usage and power rate since we sometimes want both fuel and power usage.
    """

    def __init__(
        self,
        periods: Periods,
        is_valid: TimeSeriesBoolean,
        energy_usage: TimeSeriesStreamDayRate,
        power: TimeSeriesStreamDayRate | None,
    ):
        super().__init__(periods=periods, is_valid=is_valid, energy_usage=energy_usage, power=power)
        self.periods = periods
        self.is_valid = is_valid
        self.energy_usage = energy_usage
        self.power = power


class GenericComponentResult(CommonResultBase):
    typ: Literal["generc"] = "generc"

    def __init__(
        self,
        periods: Periods,
        is_valid: TimeSeriesBoolean,
        energy_usage: TimeSeriesStreamDayRate,
        power: TimeSeriesStreamDayRate | None,
        id: str,
    ):
        super().__init__(periods=periods, is_valid=is_valid, energy_usage=energy_usage, power=power)
        self.id = id


class GeneratorSetResult(GenericComponentResult):
    """The Generator set result component."""

    typ: Literal["genset"] = "genset"

    def __init__(
        self,
        periods: Periods,
        is_valid: TimeSeriesBoolean,
        energy_usage: TimeSeriesStreamDayRate,
        power: TimeSeriesStreamDayRate | None,
        id: str,
        power_capacity_margin: TimeSeriesStreamDayRate,
    ):
        super().__init__(periods=periods, is_valid=is_valid, energy_usage=energy_usage, power=power, id=id)
        self.power_capacity_margin = power_capacity_margin


class ConsumerSystemResult(GenericComponentResult):
    typ: Literal["system"] = "system"

    def __init__(
        self,
        periods: Periods,
        is_valid: TimeSeriesBoolean,
        energy_usage: TimeSeriesStreamDayRate,
        power: TimeSeriesStreamDayRate | None,
        id: str,
        operational_settings_used: TimeSeriesInt,
        operational_settings_results: dict[int, list[Any]] | None = None,
    ):
        super().__init__(periods=periods, is_valid=is_valid, energy_usage=energy_usage, power=power, id=id)
        self.operational_settings_used = operational_settings_used
        self.operational_settings_results = operational_settings_results


class CompressorResult(GenericComponentResult):
    typ: Literal["comp"] = "comp"

    def __init__(
        self,
        periods: Periods,
        is_valid: TimeSeriesBoolean,
        energy_usage: TimeSeriesStreamDayRate,
        power: TimeSeriesStreamDayRate | None,
        id: str,
        recirculation_loss: TimeSeriesStreamDayRate,
        rate_exceeds_maximum: TimeSeriesBoolean,
    ):
        super().__init__(periods=periods, is_valid=is_valid, energy_usage=energy_usage, power=power, id=id)
        self.recirculation_loss = recirculation_loss
        self.rate_exceeds_maximum = rate_exceeds_maximum

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

    def __init__(
        self,
        periods: Periods,
        is_valid: TimeSeriesBoolean,
        energy_usage: TimeSeriesStreamDayRate,
        power: TimeSeriesStreamDayRate | None,
        id: str,
        inlet_liquid_rate_m3_per_day: TimeSeriesStreamDayRate,
        inlet_pressure_bar: TimeSeriesFloat,
        outlet_pressure_bar: TimeSeriesFloat,
        operational_head: TimeSeriesFloat,
    ):
        super().__init__(periods=periods, is_valid=is_valid, energy_usage=energy_usage, power=power, id=id)
        self.inlet_liquid_rate_m3_per_day = inlet_liquid_rate_m3_per_day
        self.inlet_pressure_bar = inlet_pressure_bar
        self.outlet_pressure_bar = outlet_pressure_bar
        self.operational_head = operational_head

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

    def __init__(
        self,
        periods: Periods,
        is_valid: TimeSeriesBoolean,
        energy_usage: TimeSeriesStreamDayRate,
        power: TimeSeriesStreamDayRate | None,
        name: str,
        inlet_liquid_rate_m3_per_day: list[float | None],
        inlet_pressure_bar: list[float | None],
        outlet_pressure_bar: list[float | None],
        operational_head: list[float | None],
    ):
        super().__init__(periods=periods, is_valid=is_valid, energy_usage=energy_usage, power=power)
        self.name = name
        self.inlet_liquid_rate_m3_per_day = inlet_liquid_rate_m3_per_day
        self.inlet_pressure_bar = inlet_pressure_bar
        self.outlet_pressure_bar = outlet_pressure_bar
        self.operational_head = operational_head

    @property
    def component_type(self):
        return ComponentType.PUMP


class CompressorModelResult(ConsumerModelResultBase):
    def __init__(
        self,
        periods: Periods,
        is_valid: TimeSeriesBoolean,
        energy_usage: TimeSeriesStreamDayRate,
        power: TimeSeriesStreamDayRate | None,
        name: str,
        rate_sm3_day: list[float | None] | list[list[float | None]],
        max_standard_rate: list[float | None] | list[list[float | None]] | None,
        stage_results: list[CompressorStageResult],
        failure_status: list[CompressorTrainCommonShaftFailureStatus | None],
        turbine_result: TurbineResult | None,
        inlet_stream_condition: CompressorStreamCondition,
        outlet_stream_condition: CompressorStreamCondition,
    ):
        super().__init__(periods=periods, is_valid=is_valid, energy_usage=energy_usage, power=power)
        self.name = name
        self.rate_sm3_day = rate_sm3_day
        self.max_standard_rate = max_standard_rate
        self.stage_results = stage_results
        self.failure_status = failure_status
        self.turbine_result = turbine_result
        self.inlet_stream_condition = inlet_stream_condition
        self.outlet_stream_condition = outlet_stream_condition

    @property
    def component_type(self):
        return ComponentType.COMPRESSOR


class GenericModelResult(ConsumerModelResultBase):
    """Generic consumer result component."""

    def __init__(
        self,
        periods: Periods,
        is_valid: TimeSeriesBoolean,
        energy_usage: TimeSeriesStreamDayRate,
        power: TimeSeriesStreamDayRate | None,
        name: str,
    ):
        super().__init__(periods=periods, is_valid=is_valid, energy_usage=energy_usage, power=power)
        self.name = name

    @property
    def component_type(self):
        return ComponentType.GENERIC


# Consumer model result is referred to as ENERGY_USAGE_MODEL in the input YAML
ConsumerModelResult = CompressorModelResult | PumpModelResult | GenericModelResult

ComponentResult = GeneratorSetResult | ConsumerSystemResult | CompressorResult | PumpResult | GenericComponentResult


class EcalcModelResult(EcalcResultBaseModel):
    """Result object holding one component for each part of the eCalc model run."""

    def __init__(
        self,
        component_result: ComponentResult,
        sub_components: list[ComponentResult],
        models: list[ConsumerModelResult],
    ):
        super().__init__(component_result=component_result, sub_components=sub_components, models=models)
        self.component_result = component_result
        self.sub_components = sub_components
        self.models = models
        self.round_values()
