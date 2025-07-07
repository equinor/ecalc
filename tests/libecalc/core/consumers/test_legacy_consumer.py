from datetime import datetime

import numpy as np
import pandas as pd
import pytest

from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    RateType,
    TimeSeriesBoolean,
    TimeSeriesFloat,
    TimeSeriesRate,
    TimeSeriesStreamDayRate,
)
from libecalc.common.variables import ExpressionEvaluator
from libecalc.core.result import EcalcModelResult
from libecalc.domain.energy import ComponentEnergyContext
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function import (
    ConsumerFunction,
    ConsumerFunctionResult,
)


class DummyEnergyContext(ComponentEnergyContext):
    def __init__(self, power_requirement: TimeSeriesFloat | None = None):
        self._power_requirement = power_requirement

    def get_power_requirement(self) -> TimeSeriesFloat | None:
        return self._power_requirement

    def get_fuel_usage(self) -> TimeSeriesStreamDayRate | None:
        raise NotImplementedError()


@pytest.fixture
def energy_context_factory():
    def create_energy_context(power_requirement: TimeSeriesFloat) -> ComponentEnergyContext:
        return DummyEnergyContext(power_requirement=power_requirement)

    return create_energy_context


@pytest.fixture
def empty_energy_context() -> ComponentEnergyContext:
    return DummyEnergyContext()


def test_fuel_consumer(tabulated_fuel_consumer_factory, expression_evaluator_factory, empty_energy_context):
    """Simple test to assert that the FuelConsumer actually runs as expected."""
    time_vector = pd.date_range(datetime(2020, 1, 1), datetime(2026, 1, 1), freq="YS").to_pydatetime().tolist()
    variables = expression_evaluator_factory.from_time_vector(
        time_vector=time_vector, variables={"RATE": [1, 1, 1, 1, 0, 0]}
    )

    tabulated_fuel_consumer = tabulated_fuel_consumer_factory(expression_evaluator=variables)
    result = tabulated_fuel_consumer.evaluate_energy_usage(context=empty_energy_context)
    result = result[tabulated_fuel_consumer.id]
    consumer_result = result.component_result

    assert consumer_result.energy_usage == TimeSeriesRate(
        periods=variables.periods,
        values=[2, 2, 2, 2, 0, 0],
        regularity=[1] * 6,
        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
        rate_type=RateType.CALENDAR_DAY,
    )
    assert consumer_result.is_valid == TimeSeriesBoolean(
        periods=variables.periods,
        values=[True] * 6,
        unit=Unit.NONE,
    )

    assert consumer_result.periods == variables.periods


def test_electricity_consumer(electricity_consumer_factory, expression_evaluator_factory, empty_energy_context):
    """Simple test to assert that the FuelConsumer actually runs as expected."""
    time_vector = pd.date_range(datetime(2020, 1, 1), datetime(2026, 1, 1), freq="YS").to_pydatetime().tolist()
    variables = expression_evaluator_factory.from_time_vector(time_vector=time_vector)
    electricity_consumer = electricity_consumer_factory(variables)

    result = electricity_consumer.evaluate_energy_usage(empty_energy_context)
    result = result[electricity_consumer.id]

    assert isinstance(result, EcalcModelResult)
    consumer_result = result.component_result
    assert consumer_result.power == TimeSeriesStreamDayRate(
        periods=variables.periods,
        values=[1, 2, 10, 0, 0, 0],
        unit=Unit.MEGA_WATT,
    )
    assert consumer_result.is_valid == TimeSeriesBoolean(
        periods=variables.periods,
        values=[True] * 6,
        unit=Unit.NONE,
    )
    assert consumer_result.periods == variables.periods


def test_electricity_consumer_mismatch_time_slots(
    electricity_consumer_factory, expression_evaluator_factory, empty_energy_context
):
    """The direct_el_consumer starts after the ElectricityConsumer is finished."""
    time_vector = pd.date_range(datetime(2000, 1, 1), datetime(2005, 1, 1), freq="YS").to_pydatetime().tolist()
    variables = expression_evaluator_factory.from_time_vector(time_vector=time_vector)
    electricity_consumer = electricity_consumer_factory(variables)

    result = electricity_consumer.evaluate_energy_usage(
        context=empty_energy_context,
    )
    consumer_result = result[electricity_consumer.id].component_result

    # The consumer itself should however return a proper result object matching the input time_vector.
    assert consumer_result.periods == variables.periods
    assert consumer_result.power == TimeSeriesStreamDayRate(
        periods=variables.periods,
        values=[0] * len(variables.periods),
        unit=Unit.MEGA_WATT,
    )
    assert consumer_result.is_valid == TimeSeriesBoolean(
        periods=variables.periods,
        values=[True] * len(variables.periods),
        unit=Unit.NONE,
    )


class NanConsumerFunction(ConsumerFunction):
    def evaluate(self, expression_evaluator: ExpressionEvaluator) -> ConsumerFunctionResult:
        assert len(expression_evaluator.get_periods()) == 6
        power = np.asarray([np.nan, np.nan, 1, np.nan, np.nan, np.nan])
        return ConsumerFunctionResult(
            power=power,
            energy_usage=power,
            periods=expression_evaluator.get_periods(),
            is_valid=np.asarray([False, False, True, False, False, False]),
        )


def test_electricity_consumer_nan_values(
    electricity_consumer_factory,
    expression_evaluator_factory,
    empty_energy_context,
):
    """1. When the resulting power starts with NaN, these values will be filled with zeros.
    2. When a valid power result is followed by NaN-values,
        then these are forward filled when extrapcorrection is True.
        If not, they are filled with zeros and extrapolation is False.
    3. Only valid power from the consumer function results are reported as valid results.

    """
    time_vector = pd.date_range(datetime(2020, 1, 1), datetime(2026, 1, 1), freq="YS").to_pydatetime().tolist()
    variables = expression_evaluator_factory.from_time_vector(time_vector=time_vector)
    electricity_consumer = electricity_consumer_factory(
        variables, TemporalModel({Period(datetime(1900, 1, 1)): NanConsumerFunction()})
    )

    result = electricity_consumer.evaluate_energy_usage(
        context=empty_energy_context,
    )
    consumer_result = result[electricity_consumer.id].component_result

    assert consumer_result.power == TimeSeriesStreamDayRate(
        periods=variables.periods,
        values=[0, 0, 1, 1, 1, 1],
        unit=Unit.MEGA_WATT,
    )
    assert consumer_result.is_valid == TimeSeriesBoolean(
        periods=variables.periods,
        values=[False, False, True, False, False, False],
        unit=Unit.NONE,
    )
