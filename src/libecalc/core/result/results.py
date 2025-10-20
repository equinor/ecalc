from __future__ import annotations

from collections.abc import Callable
from functools import reduce
from typing import TYPE_CHECKING, Any, Generic, TypeVar

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
from libecalc.domain.process.core.results import CompressorTrainResult


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

    @property
    def temporal_results(self) -> list[ConsumerFunctionResult]:
        return self._results


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

    @property
    def temporal_results(self) -> list[ConsumerSystemConsumerFunctionResult]:
        return self._results


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
        assert all(
            isinstance(result.energy_function_result, CompressorTrainResult) for result in results
        ), "Got compressor result without CompressorTrainResult"

    @property
    def temporal_results(self) -> list[ConsumerFunctionResult]:
        return self._results


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

    @property
    def temporal_results(self) -> list[ConsumerFunctionResult]:
        return self._results


ComponentResult = GeneratorSetResult | ConsumerSystemResult | CompressorResult | PumpResult | GenericComponentResult
