from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from functools import reduce
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from libecalc.common.component_type import ComponentType
from libecalc.common.time_utils import Periods
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    TimeSeries,
    TimeSeriesBoolean,
    TimeSeriesFloat,
    TimeSeriesInt,
    TimeSeriesStreamDayRate,
)

if TYPE_CHECKING:
    from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function import (
        ConsumerFunctionResult,
    )
    from libecalc.domain.infrastructure.energy_components.legacy_consumer.system import (
        ConsumerSystemConsumerFunctionResult,
    )
from libecalc.domain.process.core.results import CompressorStreamCondition, TurbineResult
from libecalc.domain.process.core.results.compressor import (
    CompressorStageResult,
    CompressorTrainCommonShaftFailureStatus,
)


class CommonResultBase:
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
        self.periods = periods
        self.is_valid = is_valid
        self.energy_usage = energy_usage
        self.power = power


class GeneratorSetResult(CommonResultBase):
    """The Generator set result component."""

    def __init__(
        self,
        periods: Periods,
        is_valid: TimeSeriesBoolean,
        energy_usage: TimeSeriesStreamDayRate,
        power: TimeSeriesStreamDayRate | None,
        id: str,
        power_capacity_margin: TimeSeriesStreamDayRate,
    ):
        super().__init__(periods=periods, is_valid=is_valid, energy_usage=energy_usage, power=power)
        self.id = id
        self.power_capacity_margin = power_capacity_margin


T = TypeVar("T", bound=TimeSeries)


class ConcatenatedProperty(Generic[T]):
    """
    Descriptor that aggregates lists of values into TimeSeries.
    """

    def __init__(
        self,
        class_: type[T],
        fill_value: Any,
        unit: Unit = None,
        accessor: Callable | None = None,
        allow_none: bool = False,
        post_processor: Callable[[T], T] | None = None,
    ):
        self._class = class_
        self._unit = unit
        self._fill_value = fill_value
        self._allow_none = allow_none

        self._accessor = accessor
        self._post_processor = post_processor

    def __set_name__(self, owner, name):
        self._name = name  # property name, used as default property access if not overridden in __init__

    def __get__(self, obj, objtype=None) -> T:
        results = obj._results

        def accessor(result):
            if self._accessor is None:
                value = getattr(result, self._name, None)
            else:
                value = self._accessor(result)

            if value is None:
                if self._allow_none:
                    return None
                return [self._fill_value] * len(result.periods)
            else:
                return value

        time_series: list[T] = []
        for result in results:
            if self._unit is None:
                unit = getattr(result, f"{self._name}_unit", None)
            else:
                unit = self._unit

            attribute = accessor(result)
            if attribute is None:
                assert self._allow_none
                return None

            assert unit is not None
            time_series.append(
                self._class(
                    values=attribute,
                    periods=result.periods,
                    unit=unit,
                )
            )

        assert len({time_serie.unit for time_serie in time_series}) == 1, "All time series must have the same unit"

        res = reduce(lambda x, y: x.extend(y), time_series).fill_values_for_new_periods(
            new_periods=obj.periods,
            fillna=self._fill_value,
        )

        if self._post_processor is not None:
            return self._post_processor(res)

        return res


class GenericComponentResult:
    energy_usage = ConcatenatedProperty(TimeSeriesStreamDayRate, fill_value=0.0)
    power = ConcatenatedProperty(TimeSeriesStreamDayRate, unit=Unit.MEGA_WATT, fill_value=0.0, allow_none=True)
    is_valid = ConcatenatedProperty(TimeSeriesBoolean, unit=Unit.NONE, fill_value=True)

    def __init__(
        self,
        periods: Periods,
        id: str,
        results: list[ConsumerFunctionResult],
    ):
        self._results = results
        self.periods = periods
        self.id = id


def convert_to_one_based_index(time_series: TimeSeriesInt) -> TimeSeriesInt:
    time_series.values = [value + 1 for value in time_series.values]
    return time_series


class ConsumerSystemResult:
    energy_usage = ConcatenatedProperty(TimeSeriesStreamDayRate, fill_value=0.0)
    power = ConcatenatedProperty(TimeSeriesStreamDayRate, unit=Unit.MEGA_WATT, fill_value=0.0, allow_none=True)
    is_valid = ConcatenatedProperty(TimeSeriesBoolean, unit=Unit.NONE, fill_value=True)
    operational_settings_used = ConcatenatedProperty(
        TimeSeriesInt,
        unit=Unit.NONE,
        fill_value=-1,
        accessor=lambda result: result.operational_setting_used,
        post_processor=convert_to_one_based_index,
    )

    def __init__(
        self,
        periods: Periods,
        id: str,
        results: list[ConsumerSystemConsumerFunctionResult],
    ):
        self._results = results
        self.periods = periods
        self.id = id


class CompressorResult:
    energy_usage = ConcatenatedProperty(TimeSeriesStreamDayRate, fill_value=0.0)
    power = ConcatenatedProperty(TimeSeriesStreamDayRate, unit=Unit.MEGA_WATT, fill_value=0.0, allow_none=True)
    is_valid = ConcatenatedProperty(TimeSeriesBoolean, unit=Unit.NONE, fill_value=True)
    recirculation_loss = ConcatenatedProperty(
        TimeSeriesStreamDayRate,
        unit=Unit.MEGA_WATT,
        accessor=lambda result: result.energy_function_result.recirculation_loss,
        fill_value=0.0,
    )
    rate_exceeds_maximum = ConcatenatedProperty(
        TimeSeriesBoolean,
        unit=Unit.NONE,
        accessor=lambda result: result.energy_function_result.rate_exceeds_maximum,
        fill_value=False,
    )

    def __init__(
        self,
        periods: Periods,
        id: str,
        results: list[ConsumerFunctionResult],
    ):
        self._results = results
        self.periods = periods
        self.id = id


class PumpResult:
    energy_usage = ConcatenatedProperty(TimeSeriesStreamDayRate, fill_value=0.0)
    power = ConcatenatedProperty(TimeSeriesStreamDayRate, unit=Unit.MEGA_WATT, fill_value=0.0, allow_none=True)
    is_valid = ConcatenatedProperty(TimeSeriesBoolean, unit=Unit.NONE, fill_value=True)
    inlet_liquid_rate_m3_per_day = ConcatenatedProperty(
        TimeSeriesStreamDayRate,
        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
        accessor=lambda result: result.energy_function_result.rate,
        fill_value=0.0,
    )
    inlet_pressure_bar = ConcatenatedProperty(
        TimeSeriesFloat,
        unit=Unit.BARA,
        accessor=lambda result: result.energy_function_result.suction_pressure,
        fill_value=0.0,
    )

    outlet_pressure_bar = ConcatenatedProperty(
        TimeSeriesFloat,
        unit=Unit.BARA,
        accessor=lambda result: result.energy_function_result.discharge_pressure,
        fill_value=0.0,
    )

    operational_head = ConcatenatedProperty(
        TimeSeriesFloat,
        unit=Unit.POLYTROPIC_HEAD_JOULE_PER_KG,
        accessor=lambda result: result.energy_function_result.operational_head,
        fill_value=0.0,
    )

    def __init__(
        self,
        periods: Periods,
        id: str,
        results: list[ConsumerFunctionResult],
    ):
        self._results = results
        self.periods = periods
        self.id = id


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
        inlet_liquid_rate_m3_per_day: list[float],
        inlet_pressure_bar: list[float],
        outlet_pressure_bar: list[float],
        operational_head: list[float],
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
        rate_sm3_day: list[float] | list[list[float]],
        max_standard_rate: list[float] | list[list[float]] | None,
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


class EcalcModelResult:
    """Result object holding one component for each part of the eCalc model run."""

    def __init__(
        self,
        component_result: ComponentResult,
        sub_components: list[ComponentResult],
        models: list[ConsumerModelResult],
    ):
        self.component_result = component_result
        self.sub_components = sub_components
        self.models = models
