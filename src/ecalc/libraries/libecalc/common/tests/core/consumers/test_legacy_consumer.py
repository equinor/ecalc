from datetime import datetime
from unittest.mock import Mock

import numpy as np
import pandas as pd
from libecalc import dto
from libecalc.common.units import Unit
from libecalc.common.utils.rates import TimeSeriesBoolean, TimeSeriesRate
from libecalc.core.consumers.legacy_consumer.component import Consumer
from libecalc.core.consumers.legacy_consumer.consumer_function import (
    ConsumerFunctionResult,
)
from libecalc.core.result import EcalcModelResult
from libecalc.dto.types import RateType


def test_compute_consumer_rate():
    """Matching the energy usage rate of the EnergyFunctionResult with the result of the parent Consumer:"""
    time_vector = pd.date_range(datetime(2020, 1, 1), datetime(2023, 1, 1), freq="YS").to_pydatetime().tolist()

    consumer_rate = Consumer.reindex_time_vector(
        values=np.array([1, 2]),
        time_vector=time_vector[1:-1],
        new_time_vector=time_vector,
    )

    assert consumer_rate.tolist() == [0, 1, 2, 0]  # Note that the consumer starts and ends 1 year before/after


def test_evaluate_consumer_time_function(direct_el_consumer):
    """Testing using a direct el consumer for simplicity."""
    consumer = Consumer(direct_el_consumer)
    time_vector = pd.date_range(datetime(2020, 1, 1), datetime(2025, 1, 1), freq="YS").to_pydatetime().tolist()
    results = consumer.evaluate_consumer_temporal_model(
        variables_map=dto.VariablesMap(time_vector=time_vector), regularity=np.ones_like(time_vector)
    )
    assert results.energy_usage.tolist() == [1, 2, 10, 0, 0, 0]
    assert results.is_valid.tolist() == [1, 1, 1, 1, 1, 1]
    assert results.time_vector.tolist() == time_vector


def test_fuel_consumer(tabulated_fuel_consumer):
    """Simple test to assert that the FuelConsumer actually runs as expected."""
    time_vector = pd.date_range(datetime(2020, 1, 1), datetime(2025, 1, 1), freq="YS").to_pydatetime().tolist()
    fuel_consumer = Consumer(tabulated_fuel_consumer)

    result = fuel_consumer.evaluate(
        variables_map=dto.VariablesMap(time_vector=time_vector, variables={"RATE": [1, 1, 1, 1, 0, 0]}),
    )
    consumer_result = result.component_result

    assert consumer_result.energy_usage == TimeSeriesRate(
        timesteps=time_vector,
        values=[2, 2, 2, 2, 0, 0],
        regularity=[1] * 6,
        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
        typ=RateType.CALENDAR_DAY,
    )
    assert consumer_result.is_valid == TimeSeriesBoolean(
        timesteps=time_vector,
        values=[True] * 6,
        unit=Unit.NONE,
    )

    assert consumer_result.timesteps == time_vector


def test_electricity_consumer(direct_el_consumer):
    """Simple test to assert that the FuelConsumer actually runs as expected."""
    electricity_consumer = Consumer(direct_el_consumer)
    time_vector = pd.date_range(datetime(2020, 1, 1), datetime(2025, 1, 1), freq="YS").to_pydatetime().tolist()
    result = electricity_consumer.evaluate(
        variables_map=dto.VariablesMap(time_vector=time_vector),
    )

    assert isinstance(result, EcalcModelResult)
    consumer_result = result.component_result
    assert consumer_result.power == TimeSeriesRate(
        timesteps=time_vector,
        values=[1, 2, 10, 0, 0, 0],
        regularity=[1] * 6,
        unit=Unit.MEGA_WATT,
    )
    assert consumer_result.is_valid == TimeSeriesBoolean(
        timesteps=time_vector,
        values=[True] * 6,
        unit=Unit.NONE,
    )
    assert consumer_result.timesteps == time_vector


def test_electricity_consumer_mismatch_time_slots(direct_el_consumer):
    """The direct_el_consumer starts after the ElectricityConsumer is finished."""
    time_vector = pd.date_range(datetime(2000, 1, 1), datetime(2005, 1, 1), freq="YS").to_pydatetime().tolist()
    electricity_consumer = Consumer(direct_el_consumer)

    result = electricity_consumer.evaluate(
        variables_map=dto.VariablesMap(time_vector=time_vector),
    )
    consumer_result = result.component_result

    # The consumer itself should however return a proper result object matching the input time_vector.
    assert consumer_result.timesteps == time_vector
    assert consumer_result.power == TimeSeriesRate(
        timesteps=time_vector,
        values=[0] * len(time_vector),
        regularity=[1] * 6,
        unit=Unit.MEGA_WATT,
    )
    assert consumer_result.is_valid == TimeSeriesBoolean(
        timesteps=time_vector,
        values=[True] * len(time_vector),
        unit=Unit.NONE,
    )


def test_electricity_consumer_nan_values(direct_el_consumer):
    """1. When the resulting power starts with NaN, these values will be filled with zeros.
    2. When a valid power result is followed by NaN-values,
        then these are forward filled when extrapcorrection is True.
        If not, they are filled with zeros and extrapolation is False.
    3. Only valid power from the consumer function results are reported as valid results.

    :param direct_el_consumer:
    :return:
    """
    time_vector = pd.date_range(datetime(2020, 1, 1), datetime(2025, 1, 1), freq="YS").to_pydatetime().tolist()
    power = np.array([np.nan, np.nan, 1, np.nan, np.nan, np.nan])
    electricity_consumer = Consumer(direct_el_consumer)
    consumer_function_result = ConsumerFunctionResult(
        power=power,
        energy_usage=power,
        time_vector=np.asarray(time_vector),
        is_valid=np.asarray([False, False, True, False, False, False]),
    )

    electricity_consumer.evaluate_consumer_temporal_model = Mock(return_value=consumer_function_result)

    result = electricity_consumer.evaluate(
        variables_map=dto.VariablesMap(time_vector=time_vector),
    )
    consumer_result = result.component_result

    assert consumer_result.power == TimeSeriesRate(
        timesteps=time_vector,
        values=[0, 0, 1, 1, 1, 1],
        regularity=[1] * 6,
        unit=Unit.MEGA_WATT,
    )
    assert consumer_result.is_valid == TimeSeriesBoolean(
        timesteps=time_vector,
        values=[False, False, True, False, False, False],
        unit=Unit.NONE,
    )
