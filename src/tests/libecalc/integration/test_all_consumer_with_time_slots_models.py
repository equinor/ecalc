import itertools
from datetime import datetime
from typing import Dict, List

import numpy as np
import pytest
from libecalc import dto
from libecalc.core.consumers.legacy_consumer.component import Consumer
from libecalc.core.energy_calculator import EnergyCalculator
from libecalc.core.graph_result import GraphResult
from libecalc.core.result import CompressorModelResult, GenericModelResult


def test_mismatching_time_slots_within_a_consumer(time_slot_electricity_consumer_with_changing_model_type):
    """In case of mismatching time vector when ENERGY_USAGE_MODEL is outside of the vector of the CONSUMER.
    Then we still want a result.
    """
    el_consumer = Consumer(consumer_dto=time_slot_electricity_consumer_with_changing_model_type)
    time_vector = [datetime(1900, 1, 1), datetime(1901, 1, 1)]
    result = el_consumer.evaluate(variables_map=dto.VariablesMap(time_vector=time_vector, variables={}))
    consumer_result = result.component_result
    assert consumer_result.timesteps == time_vector
    assert consumer_result.power.values == [0, 0]


def test_time_slots_with_changing_model(time_slot_electricity_consumer_with_changing_model_type):
    """When using different ENERGY_USAGE_MODELs under a CONSUMER, the detailed energy_functions_results
    will be a list of results and not a merged object.
    """
    el_consumer = Consumer(consumer_dto=time_slot_electricity_consumer_with_changing_model_type)
    input_variables_dict: Dict[str, List[float]] = {"RATE": np.linspace(start=2000000, stop=6000000, num=10).tolist()}

    result = el_consumer.evaluate(
        variables_map=dto.VariablesMap(
            time_vector=[datetime(year, 1, 1) for year in range(2015, 2025)], variables=input_variables_dict
        ),
    )

    consumer_result = result.component_result

    model_results = result.models
    assert len(model_results) == 3

    first, second, third = model_results

    assert len(consumer_result.timesteps) == 10

    # First two timesteps are extrapolated in consumer result
    assert (
        list(itertools.chain(*[model_result.timesteps for model_result in result.models]))
        == consumer_result.timesteps[2:]
    )

    assert first.timesteps == [datetime(2017, 1, 1)]
    assert second.timesteps == [
        datetime(2018, 1, 1),
        datetime(2019, 1, 1),
        datetime(2020, 1, 1),
        datetime(2021, 1, 1),
        datetime(2022, 1, 1),
        datetime(2023, 1, 1),
    ]
    assert third.timesteps == [datetime(2024, 1, 1)]

    assert isinstance(first, GenericModelResult)
    assert isinstance(second, CompressorModelResult)
    assert isinstance(third, GenericModelResult)


def test_time_slots_with_non_changing_model(time_slot_electricity_consumer_with_same_model_type):
    """When using same ENERGY_USAGE_MODEL types under a CONSUMER, the detailed energy_functions_results
    will not be a merged result object.
    """
    el_consumer = Consumer(consumer_dto=time_slot_electricity_consumer_with_same_model_type)
    input_variables_dict: Dict[str, List[float]] = {}

    result = el_consumer.evaluate(
        variables_map=dto.VariablesMap(
            time_vector=[datetime(year, 1, 1) for year in range(2017, 2025)], variables=input_variables_dict
        ),
    )
    consumer_result = result.component_result

    model_results = result.models
    assert len(model_results) == 3

    first, second, third = model_results

    assert len(consumer_result.timesteps) == 8

    assert (
        list(itertools.chain(*[model_result.timesteps for model_result in result.models])) == consumer_result.timesteps
    )

    assert first.timesteps == [datetime(2017, 1, 1), datetime(2018, 1, 1)]
    assert second.timesteps == [
        datetime(2019, 1, 1),
        datetime(2020, 1, 1),
        datetime(2021, 1, 1),
        datetime(2022, 1, 1),
        datetime(2023, 1, 1),
    ]
    assert third.timesteps == [datetime(2024, 1, 1)]

    assert isinstance(first, GenericModelResult)
    assert isinstance(second, GenericModelResult)
    assert isinstance(third, GenericModelResult)


def test_time_slots_consumer_system_with_non_changing_model(time_slots_simplified_compressor_system):
    """When using compatible TYPEs within a CONSUMER SYSTEM then the result."""
    start_year = 2015
    time_steps = 10
    el_consumer = Consumer(consumer_dto=time_slots_simplified_compressor_system)
    input_variables_dict: Dict[str, List[float]] = {
        "RATE": [1800000 - (x * 100000) for x in range(10)]  # 1 000 000 -> 100 000
    }

    result = el_consumer.evaluate(
        variables_map=dto.VariablesMap(
            time_vector=[datetime(year, 1, 1) for year in range(start_year, start_year + time_steps)],
            variables=input_variables_dict,
        ),
    )
    consumer_result = result.component_result

    np.testing.assert_allclose(
        consumer_result.power.values,
        [8.689979, 8.689979, 8.689979, 8.689979, 4.629882, 4.555372, 4.481052, 4.406923, 4.344989, 4.344989],
        rtol=1e-3,
    )


@pytest.mark.snapshot
def test_all_consumer_with_time_slots_models_results(consumer_with_time_slots_models_dto, rounded_snapshot):
    ecalc_model = consumer_with_time_slots_models_dto.ecalc_model
    variables = consumer_with_time_slots_models_dto.variables

    graph = ecalc_model.get_graph()
    energy_calculator = EnergyCalculator(graph=graph)
    consumer_results = energy_calculator.evaluate_energy_usage(variables)
    emission_results = energy_calculator.evaluate_emissions(
        variables_map=variables,
        consumer_results=consumer_results,
    )
    result = GraphResult(
        graph=graph,
        consumer_results=consumer_results,
        variables_map=variables,
        emission_results=emission_results,
    ).get_results()

    snapshot_name = "all_consumer_with_time_slots_models_v3.json"
    rounded_snapshot(data=result.dict(), snapshot_name=snapshot_name)
