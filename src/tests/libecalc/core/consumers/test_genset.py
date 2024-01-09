from datetime import datetime

import numpy as np
import pandas as pd
from libecalc import dto
from libecalc.application.energy_calculator import EnergyCalculator
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    TimeSeriesBoolean,
    TimeSeriesStreamDayRate,
)
from libecalc.core.consumers.generator_set import Genset
from libecalc.core.result.results import GenericComponentResult


def test_genset_out_of_capacity(genset_2mw_dto, fuel_dto):
    """Testing a genset at capacity, at zero and above capacity.

    Note that extrapcorrection does not have any effect on the Genset itself - but may have an effect on the elconsumer.
    """
    time_vector = pd.date_range(datetime(2020, 1, 1), datetime(2025, 1, 1), freq="YS").to_pydatetime().tolist()

    graph = genset_2mw_dto.get_graph()
    energy_calculator = EnergyCalculator(graph=graph)
    variables = dto.VariablesMap(time_vector=time_vector)
    consumer_results = energy_calculator.evaluate_energy_usage(variables)

    generator_set_result = consumer_results[genset_2mw_dto.id].component_result
    components = [consumer_results[successor].component_result for successor in graph.get_successors(genset_2mw_dto.id)]

    # Note that this discrepancy between power rate and fuel rate will normally not happen, since the el-consumer
    # will also interpolate the same way as the genset does.
    assert generator_set_result.power == TimeSeriesStreamDayRate(
        timesteps=time_vector,
        values=[1, 2, 10, 0, 0, 0],
        unit=Unit.MEGA_WATT,
    )
    assert generator_set_result.is_valid == TimeSeriesBoolean(
        timesteps=time_vector,
        values=[True, True, False, True, True, True],
        unit=Unit.NONE,
    )
    assert isinstance(components[0], GenericComponentResult)

    emission_results = energy_calculator.evaluate_emissions(variables_map=variables, consumer_results=consumer_results)

    genset_emissions = emission_results[genset_2mw_dto.id]
    assert genset_emissions["co2"].rate.values == [0.001, 0.002, 0.002, 0, 0, 0]
    assert generator_set_result.timesteps == time_vector


def test_genset_with_elconsumer_nan_results(genset_2mw_dto, fuel_dto):
    """Testing what happens when the el-consumers has nan-values in power. -> Genset should not do anything."""
    time_vector = pd.date_range(datetime(2020, 1, 1), datetime(2025, 1, 1), freq="YS").to_pydatetime().tolist()
    genset = Genset(genset_2mw_dto)

    results = genset.evaluate(
        variables_map=dto.VariablesMap(time_vector=time_vector),
        power_requirement=np.asarray([np.nan, np.nan, 0.5, 0.5, np.nan, np.nan]),
    )

    # The Genset is not supposed to handle NaN-values from the el-consumers.
    np.testing.assert_equal(results.power.values, [np.nan, np.nan, 0.5, 0.5, np.nan, np.nan])
    assert results.power.unit == Unit.MEGA_WATT
    assert results.power.timesteps == time_vector

    # The resulting fuel rate will be zero and the result is invalid for the NaN-timesteps.
    assert results.energy_usage == TimeSeriesStreamDayRate(
        timesteps=time_vector,
        values=[0, 0, 0.6, 0.6, 0.0, 0.0],
        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
    )
    assert results.is_valid == TimeSeriesBoolean(
        timesteps=time_vector,
        values=[False, False, True, True, False, False],
        unit=Unit.NONE,
    )


def test_genset_outside_capacity(genset_2mw_dto, fuel_dto):
    """Testing what happens when the power rate is outside of genset capacity. -> Genset will extrapolate (forward fill)."""
    time_vector = pd.date_range(datetime(2020, 1, 1), datetime(2025, 1, 1), freq="YS").to_pydatetime().tolist()
    genset = Genset(genset_2mw_dto)

    results = genset.evaluate(
        variables_map=dto.VariablesMap(time_vector=time_vector),
        power_requirement=np.asarray([1, 2, 3, 4, 5, 6]),
    )

    # The genset will still report power rate
    assert results.power == TimeSeriesStreamDayRate(
        timesteps=time_vector,
        values=[1, 2, 3, 4, 5, 6],
        unit=Unit.MEGA_WATT,
    )

    # But the fuel rate will only be valid for the first step. The rest is extrapolated.
    assert results.energy_usage == TimeSeriesStreamDayRate(
        timesteps=time_vector,
        values=[1, 2, 2, 2, 2, 2],
        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
    )
    assert results.is_valid == TimeSeriesBoolean(
        timesteps=time_vector,
        values=[True, True, False, False, False, False],
        unit=Unit.NONE,
    )


def test_genset_late_startup(genset_1000mw_late_startup_dto, fuel_dto):
    time_vector = pd.date_range(datetime(2020, 1, 1), datetime(2025, 1, 1), freq="YS").to_pydatetime().tolist()

    graph = genset_1000mw_late_startup_dto.get_graph()
    energy_calculator = EnergyCalculator(graph)
    consumer_results = energy_calculator.evaluate_energy_usage(variables_map=dto.VariablesMap(time_vector=time_vector))

    generator_set_result = consumer_results[genset_1000mw_late_startup_dto.id].component_result
    components = [
        consumer_results[successor].component_result
        for successor in graph.get_successors(genset_1000mw_late_startup_dto.id)
    ]

    assert generator_set_result.power == TimeSeriesStreamDayRate(
        timesteps=time_vector,
        values=[1.0, 2.0, 10.0, 0.0, 0.0, 0.0],
        unit=Unit.MEGA_WATT,
    )

    # Note that the genset is not able to deliver the power rate demanded by the el-consumer(s) for the two
    # first time-steps before the genset is activated in 2022.
    assert generator_set_result.energy_usage == TimeSeriesStreamDayRate(
        timesteps=time_vector,
        values=[0.0, 0.0, 10.0, 0.0, 0.0, 0.0],
        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
    )
    assert generator_set_result.is_valid == TimeSeriesBoolean(
        timesteps=time_vector,
        values=[False, False, True, True, True, True],
        unit=Unit.NONE,
    )
    np.testing.assert_equal(components[0].power.values, [1.0, 2.0, 10.0, 0.0, 0.0, 0.0])
