from datetime import datetime
from unittest.mock import Mock

import numpy as np
import pandas as pd

from libecalc.common.temporal_model import TemporalModel
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    RateType,
    TimeSeriesBoolean,
    TimeSeriesRate,
    TimeSeriesStreamDayRate,
)
from libecalc.core.result import EcalcModelResult
from libecalc.domain.infrastructure.energy_components.legacy_consumer.component import Consumer
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function import (
    ConsumerFunctionResult,
)
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function_mapper import EnergyModelMapper
from libecalc.domain.regularity import Regularity


def test_evaluate_consumer_time_function(direct_el_consumer, expression_evaluator_factory):
    """Testing using a direct el consumer for simplicity."""
    time_vector = pd.date_range(datetime(2020, 1, 1), datetime(2026, 1, 1), freq="YS").to_pydatetime().tolist()
    variables = expression_evaluator_factory.from_time_vector(time_vector=time_vector)
    direct_el_consumer = direct_el_consumer(variables)
    consumer = Consumer(
        id=direct_el_consumer.id,
        name=direct_el_consumer.name,
        component_type=direct_el_consumer.component_type,
        regularity=direct_el_consumer.regularity,
        consumes=direct_el_consumer.consumes,
        energy_usage_model=TemporalModel(
            {
                start_time: EnergyModelMapper.from_dto_to_domain(model)
                for start_time, model in direct_el_consumer.energy_usage_model.items()
            }
        ),
    )

    results = consumer.evaluate_consumer_temporal_model(
        expression_evaluator=variables,
        regularity=Regularity(expression_evaluator=variables, target_period=variables.get_period(), expression_input=1),
    )
    results = consumer.aggregate_consumer_function_results(results)
    assert results.energy_usage.tolist() == [1, 2, 10, 0, 0, 0]
    assert results.is_valid.tolist() == [1, 1, 1, 1, 1, 1]
    assert results.periods == variables.periods


def test_fuel_consumer(tabulated_fuel_consumer, expression_evaluator_factory):
    """Simple test to assert that the FuelConsumer actually runs as expected."""
    time_vector = pd.date_range(datetime(2020, 1, 1), datetime(2026, 1, 1), freq="YS").to_pydatetime().tolist()
    variables = expression_evaluator_factory.from_time_vector(
        time_vector=time_vector, variables={"RATE": [1, 1, 1, 1, 0, 0]}
    )
    fuel_consumer = Consumer(
        id=tabulated_fuel_consumer.id,
        name=tabulated_fuel_consumer.name,
        component_type=tabulated_fuel_consumer.component_type,
        regularity=tabulated_fuel_consumer.regularity,
        consumes=tabulated_fuel_consumer.consumes,
        energy_usage_model=TemporalModel(
            {
                start_time: EnergyModelMapper.from_dto_to_domain(model)
                for start_time, model in tabulated_fuel_consumer.energy_usage_model.items()
            }
        ),
    )

    result = fuel_consumer.evaluate(
        expression_evaluator=variables,
    )
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


def test_electricity_consumer(direct_el_consumer, expression_evaluator_factory):
    """Simple test to assert that the FuelConsumer actually runs as expected."""
    time_vector = pd.date_range(datetime(2020, 1, 1), datetime(2026, 1, 1), freq="YS").to_pydatetime().tolist()
    variables = expression_evaluator_factory.from_time_vector(time_vector=time_vector)
    direct_el_consumer = direct_el_consumer(variables)

    electricity_consumer = Consumer(
        id=direct_el_consumer.id,
        name=direct_el_consumer.name,
        component_type=direct_el_consumer.component_type,
        regularity=direct_el_consumer.regularity,
        consumes=direct_el_consumer.consumes,
        energy_usage_model=TemporalModel(
            {
                start_time: EnergyModelMapper.from_dto_to_domain(model)
                for start_time, model in direct_el_consumer.energy_usage_model.items()
            }
        ),
    )

    result = electricity_consumer.evaluate(
        expression_evaluator=variables,
    )

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


def test_electricity_consumer_mismatch_time_slots(direct_el_consumer, expression_evaluator_factory):
    """The direct_el_consumer starts after the ElectricityConsumer is finished."""
    time_vector = pd.date_range(datetime(2000, 1, 1), datetime(2005, 1, 1), freq="YS").to_pydatetime().tolist()
    variables = expression_evaluator_factory.from_time_vector(time_vector=time_vector)
    direct_el_consumer = direct_el_consumer(variables)
    electricity_consumer = Consumer(
        id=direct_el_consumer.id,
        name=direct_el_consumer.name,
        component_type=direct_el_consumer.component_type,
        regularity=direct_el_consumer.regularity,
        consumes=direct_el_consumer.consumes,
        energy_usage_model=TemporalModel(
            {
                start_time: EnergyModelMapper.from_dto_to_domain(model)
                for start_time, model in direct_el_consumer.energy_usage_model.items()
            }
        ),
    )

    result = electricity_consumer.evaluate(
        expression_evaluator=variables,
    )
    consumer_result = result.component_result

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


def test_electricity_consumer_nan_values(direct_el_consumer, expression_evaluator_factory):
    """1. When the resulting power starts with NaN, these values will be filled with zeros.
    2. When a valid power result is followed by NaN-values,
        then these are forward filled when extrapcorrection is True.
        If not, they are filled with zeros and extrapolation is False.
    3. Only valid power from the consumer function results are reported as valid results.

    :param direct_el_consumer:
    :return:
    """
    time_vector = pd.date_range(datetime(2020, 1, 1), datetime(2026, 1, 1), freq="YS").to_pydatetime().tolist()
    variables = expression_evaluator_factory.from_time_vector(time_vector=time_vector)
    direct_el_consumer = direct_el_consumer(variables)
    power = np.array([np.nan, np.nan, 1, np.nan, np.nan, np.nan])
    electricity_consumer = Consumer(
        id=direct_el_consumer.id,
        name=direct_el_consumer.name,
        component_type=direct_el_consumer.component_type,
        regularity=direct_el_consumer.regularity,
        consumes=direct_el_consumer.consumes,
        energy_usage_model=TemporalModel(
            {
                start_time: EnergyModelMapper.from_dto_to_domain(model)
                for start_time, model in direct_el_consumer.energy_usage_model.items()
            }
        ),
    )
    consumer_function_result = ConsumerFunctionResult(
        power=power,
        energy_usage=power,
        periods=variables.periods,
        is_valid=np.asarray([False, False, True, False, False, False]),
    )

    electricity_consumer.evaluate_consumer_temporal_model = Mock(return_value=[consumer_function_result])

    result = electricity_consumer.evaluate(
        expression_evaluator=variables,
    )
    consumer_result = result.component_result

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
