from datetime import datetime

import numpy as np
import pytest
from numpy.typing import NDArray

from libecalc.common.time_utils import Periods
from libecalc.common.units import Unit
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system import ConsumerSystemConsumerFunction
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.consumer_function import SystemComponent
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.operational_setting import (
    ConsumerSystemOperationalSettingExpressions,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.results import SystemComponentResult
from libecalc.domain.time_series_flow_rate import TimeSeriesFlowRate
from libecalc.domain.time_series_fluid_density import TimeSeriesFluidDensity
from libecalc.domain.time_series_pressure import TimeSeriesPressure


@pytest.fixture
def periods_factory():
    def create_periods(length: int) -> Periods:
        times = [datetime(2020 + i, 1, 1) for i in range(length + 1)]
        return Periods.create_periods(times=times, include_before=False, include_after=False)

    return create_periods


@pytest.fixture
def values_factory():
    def create_value(length: int = None) -> list[float]:
        if length is None:
            return [5]
        return [5] * length

    return create_value


class DirectTimeSeriesPressure(TimeSeriesPressure):
    def __init__(self, periods: Periods, values: list[float]):
        self._values = values
        self._periods = periods

    def get_periods(self) -> Periods:
        return self._periods

    def get_values(self) -> list[float]:
        return self._values


@pytest.fixture
def time_series_pressure_factory(periods_factory):
    def create_time_series_pressure(periods: Periods = None, values: list[float] = None) -> TimeSeriesPressure:
        if values is None:
            values = values_factory()

        if periods is None:
            periods = periods_factory(length=len(values))
        return DirectTimeSeriesPressure(periods=periods, values=values)

    return create_time_series_pressure


class DirectTimeSeriesFlowRate(TimeSeriesFlowRate):
    def __init__(self, periods: Periods, values: list[float]):
        self._values = values
        self._periods = periods

    def get_periods(self) -> Periods:
        return self._periods

    def get_stream_day_values(self) -> list[float]:
        return self._values


@pytest.fixture
def time_series_flow_rate_factory(values_factory, periods_factory):
    def create_time_series_flow_rate(periods: Periods = None, values: list[float] = None) -> TimeSeriesFlowRate:
        if values is None:
            values = values_factory()

        if periods is None:
            periods = periods_factory(length=len(values))

        return DirectTimeSeriesFlowRate(periods=periods, values=values)

    return create_time_series_flow_rate


class DirectTimeSeriesFluidDensity(TimeSeriesFluidDensity):
    def __init__(self, periods: Periods, values: list[float]):
        self._values = values
        self._periods = periods

    def get_periods(self) -> Periods:
        return self._periods

    def get_values(self) -> list[float]:
        return self._values


@pytest.fixture
def time_series_density_factory(periods_factory):
    def create_time_series_density(periods: Periods = None, values: list[float] = None) -> TimeSeriesFluidDensity:
        if values is None:
            values = values_factory()

        if periods is None:
            periods = periods_factory(length=len(values))
        return DirectTimeSeriesFluidDensity(periods=periods, values=values)

    return create_time_series_density


class DummySystemComponentResult(SystemComponentResult):
    def __init__(
        self,
        rate: NDArray[np.float64],
        is_valid: list[bool],
        energy_usage: list[float] = None,
        power: list[float] | None = None,
    ):
        self._rate = rate
        self._is_valid = is_valid
        self.energy_usage: list[float] = energy_usage or [5] * len(rate)
        self.power: list[float] | None = power

    def __len__(self) -> int:
        return len(self._rate)

    @property
    def is_valid(self) -> list[bool]:
        return self._is_valid

    @property
    def energy_usage_unit(self) -> Unit:
        return Unit.STANDARD_CUBIC_METER_PER_DAY


class DummySystemComponent(SystemComponent):
    def __init__(
        self,
        name: str,
        max_rate: list[float] = None,
        is_valid: list[bool] = None,
        energy_usage: list[float] = None,
        power: list[float] | None = None,
    ):
        self._name = name
        self._max_rate = max_rate
        self._is_valid = is_valid
        self._energy_usage = energy_usage
        self._power = power

    def get_max_standard_rate(
        self,
        suction_pressure: NDArray[np.float64],
        discharge_pressure: NDArray[np.float64],
        fluid_density: NDArray[np.float64] = None,
    ):
        if self._max_rate is None:
            return np.array([5] * len(suction_pressure))
        return np.asarray(self._max_rate)

    @property
    def name(self) -> str:
        return self._name

    def evaluate(
        self,
        rate: NDArray[np.float64],
        suction_pressure: NDArray[np.float64],
        discharge_pressure: NDArray[np.float64],
        fluid_density: NDArray[np.float64] = None,
    ) -> SystemComponentResult:
        max_rate = self.get_max_standard_rate(suction_pressure, discharge_pressure, fluid_density)
        return DummySystemComponentResult(
            rate,
            is_valid=self._is_valid or [rate[i] <= max_rate[i] for i in range(len(rate))],
            energy_usage=self._energy_usage,
            power=self._power,
        )


@pytest.fixture
def system_component_factory():
    def create_system_component(
        name: str = "SystemComponent1",
        max_rate: list[float] = None,
        is_valid: list[bool] = None,
        energy_usage: list[float] = None,
        power: list[float] | None = None,
    ):
        return DummySystemComponent(
            name,
            max_rate=max_rate,
            is_valid=is_valid,
            energy_usage=energy_usage,
            power=power,
        )

    return create_system_component


@pytest.fixture
def system_factory():
    def create_system(
        system_components: list[SystemComponent],
        operational_settings: list[ConsumerSystemOperationalSettingExpressions],
    ):
        return ConsumerSystemConsumerFunction(
            consumer_components=system_components,
            operational_settings_expressions=operational_settings,
        )

    return create_system
