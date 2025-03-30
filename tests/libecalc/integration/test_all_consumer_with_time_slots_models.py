import itertools
import json
import math
from datetime import datetime

import numpy as np
import pytest

from libecalc.application.energy_calculator import EnergyCalculator
from libecalc.application.graph_result import GraphResult
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period, Periods
from libecalc.common.utils.rates import TimeSeriesBoolean, TimeSeriesStreamDayRate
from libecalc.common.variables import VariablesMap
from libecalc.domain.infrastructure.energy_components.legacy_consumer.component import Consumer
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function_mapper import EnergyModelMapper
from libecalc.core.result import CompressorModelResult, GenericModelResult
from libecalc.presentation.json_result.mapper import get_asset_result


def test_mismatching_time_slots_within_a_consumer(time_slot_electricity_consumer_with_changing_model_type):
    """In case of mismatching time vector when ENERGY_USAGE_MODEL is outside of the vector of the CONSUMER.
    Then we still want a result.
    """
    time_vector = [datetime(1900, 1, 1), datetime(1901, 1, 1), datetime(1902, 1, 1)]
    expression_evaluator = VariablesMap(time_vector=time_vector, variables={})
    consumer = time_slot_electricity_consumer_with_changing_model_type(time_vector=time_vector)
    el_consumer = Consumer(
        id=consumer.id,
        name=consumer.name,
        component_type=consumer.component_type,
        regularity=TemporalModel(consumer.regularity),
        consumes=consumer.consumes,
        energy_usage_model=TemporalModel(
            {
                start_time: EnergyModelMapper.from_dto_to_domain(model)
                for start_time, model in consumer.energy_usage_model.items()
            }
        ),
    )

    result = el_consumer.evaluate(expression_evaluator=expression_evaluator)
    consumer_result = result.component_result
    assert consumer_result.periods == expression_evaluator.get_periods()
    assert consumer_result.power.values == [0, 0]


def test_time_slots_with_changing_model(time_slot_electricity_consumer_with_changing_model_type):
    """When using different ENERGY_USAGE_MODELs under a CONSUMER, the detailed energy_functions_results
    will be a list of results and not a merged object.
    """
    input_variables_dict: dict[str, list[float]] = {"RATE": np.linspace(start=2000000, stop=6000000, num=10).tolist()}
    expression_evaluator = VariablesMap(
        time_vector=[datetime(year, 1, 1) for year in range(2015, 2026)], variables=input_variables_dict
    )
    consumer = time_slot_electricity_consumer_with_changing_model_type(
        time_vector=expression_evaluator.time_vector, variables=input_variables_dict
    )

    el_consumer = Consumer(
        id=consumer.id,
        name=consumer.name,
        component_type=consumer.component_type,
        regularity=TemporalModel(consumer.regularity),
        consumes=consumer.consumes,
        energy_usage_model=TemporalModel(
            {
                start_time: EnergyModelMapper.from_dto_to_domain(model)
                for start_time, model in consumer.energy_usage_model.items()
            }
        ),
    )

    result = el_consumer.evaluate(expression_evaluator=expression_evaluator)

    consumer_result = result.component_result

    model_results = result.models
    assert len(model_results) == 3

    first, second, third = model_results

    assert len(consumer_result.periods) == 10

    # First two periods are extrapolated in consumer result
    assert (
        list(itertools.chain(*[model_result.periods for model_result in result.models]))
        == consumer_result.periods.periods[2:]
    )

    assert first.periods == Periods(
        [
            Period(
                start=datetime(2017, 1, 1),
                end=datetime(2018, 1, 1),
            )
        ]
    )
    assert second.periods == Periods.create_periods(
        times=[
            datetime(2018, 1, 1),
            datetime(2019, 1, 1),
            datetime(2020, 1, 1),
            datetime(2021, 1, 1),
            datetime(2022, 1, 1),
            datetime(2023, 1, 1),
            datetime(2024, 1, 1),
        ],
        include_before=False,
        include_after=False,
    )
    assert third.periods == Periods(
        [
            Period(
                start=datetime(2024, 1, 1),
                end=datetime(2025, 1, 1),
            )
        ]
    )

    assert isinstance(first, GenericModelResult)
    assert isinstance(second, CompressorModelResult)
    assert isinstance(third, GenericModelResult)


def test_time_slots_with_non_changing_model(time_slot_electricity_consumer_with_same_model_type):
    """When using same ENERGY_USAGE_MODEL types under a CONSUMER, the detailed energy_functions_results
    will not be a merged result object.
    """
    input_variables_dict: dict[str, list[float]] = {}
    expression_evaluator = VariablesMap(
        time_vector=[datetime(year, 1, 1) for year in range(2017, 2026)], variables=input_variables_dict
    )
    consumer = time_slot_electricity_consumer_with_same_model_type(
        time_vector=expression_evaluator.time_vector, variables=input_variables_dict
    )

    el_consumer = Consumer(
        id=consumer.id,
        name=consumer.name,
        component_type=consumer.component_type,
        regularity=TemporalModel(consumer.regularity),
        consumes=consumer.consumes,
        energy_usage_model=TemporalModel(
            {
                start_time: EnergyModelMapper.from_dto_to_domain(model)
                for start_time, model in consumer.energy_usage_model.items()
            }
        ),
    )

    result = el_consumer.evaluate(expression_evaluator=expression_evaluator)
    consumer_result = result.component_result

    model_results = result.models
    assert len(model_results) == 3

    first, second, third = model_results

    assert len(consumer_result.periods) == 8

    assert (
        list(itertools.chain(*[model_result.periods for model_result in result.models]))
        == consumer_result.periods.periods
    )

    assert first.periods == Periods(
        [
            Period(
                start=datetime(2017, 1, 1),
                end=datetime(2018, 1, 1),
            ),
            Period(
                start=datetime(2018, 1, 1),
                end=datetime(2019, 1, 1),
            ),
        ]
    )
    assert second.periods == Periods.create_periods(
        times=[
            datetime(2019, 1, 1),
            datetime(2020, 1, 1),
            datetime(2021, 1, 1),
            datetime(2022, 1, 1),
            datetime(2023, 1, 1),
            datetime(2024, 1, 1),
        ],
        include_before=False,
        include_after=False,
    )
    assert third.periods == Periods(
        [
            Period(
                start=datetime(2024, 1, 1),
                end=datetime(2025, 1, 1),
            )
        ]
    )

    assert isinstance(first, GenericModelResult)
    assert isinstance(second, GenericModelResult)
    assert isinstance(third, GenericModelResult)


def test_time_slots_consumer_system_with_non_changing_model(time_slots_simplified_compressor_system):
    """When using compatible TYPEs within a CONSUMER SYSTEM then the result."""
    start_year = 2015
    time_steps = 10
    input_variables_dict: dict[str, list[float]] = {
        "RATE": [1800000 - (x * 100000) for x in range(10)]  # 1 000 000 -> 100 000
    }
    expression_evaluator = VariablesMap(
        time_vector=[datetime(year, 1, 1) for year in range(start_year, start_year + time_steps + 1)],
        variables=input_variables_dict,
    )
    consumer = time_slots_simplified_compressor_system(
        time_vector=expression_evaluator.time_vector, variables=input_variables_dict
    )

    el_consumer = Consumer(
        id=consumer.id,
        name=consumer.name,
        component_type=consumer.component_type,
        regularity=TemporalModel(consumer.regularity),
        consumes=consumer.consumes,
        energy_usage_model=TemporalModel(
            {
                period: EnergyModelMapper.from_dto_to_domain(model)
                for period, model in consumer.energy_usage_model.items()
            }
        ),
    )

    result = el_consumer.evaluate(expression_evaluator=expression_evaluator)
    consumer_result = result.component_result

    np.testing.assert_allclose(
        consumer_result.power.values,
        [8.689979, 8.689979, 8.689979, 8.689979, 4.629882, 4.555372, 4.481052, 4.406923, 4.344989, 4.344989],
        rtol=1e-3,
    )


@pytest.mark.snapshot
def test_all_consumer_with_time_slots_models_results(
    consumer_with_time_slots_models_dto, rounded_snapshot, energy_model_from_dto_factory
):
    ecalc_model = consumer_with_time_slots_models_dto.ecalc_model
    variables = consumer_with_time_slots_models_dto.variables

    graph = ecalc_model.get_graph()
    energy_calculator = EnergyCalculator(
        energy_model=energy_model_from_dto_factory(ecalc_model), expression_evaluator=variables
    )
    consumer_results = energy_calculator.evaluate_energy_usage()
    emission_results = energy_calculator.evaluate_emissions()
    graph_result = GraphResult(
        graph=graph,
        consumer_results=consumer_results,
        variables_map=variables,
        emission_results=emission_results,
    )
    asset_result = get_asset_result(graph_result).model_dump()
    snapshot_name = "all_consumer_with_time_slots_models_v3.json"
    rounded_snapshot(data=asset_result, snapshot_name=snapshot_name)
