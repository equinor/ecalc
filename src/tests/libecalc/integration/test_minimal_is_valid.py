from datetime import datetime

import pytest

from libecalc.application.energy_calculator import EnergyCalculator
from libecalc.application.graph_result import GraphResult
from libecalc.common.variables import VariablesMap
from libecalc.presentation.json_result.mapper import get_asset_result
from libecalc.presentation.json_result.result import EcalcModelResult


@pytest.fixture
def minimal_asset_result(minimal_model_dto_factory):
    minimal_dto = minimal_model_dto_factory()
    graph = minimal_dto.get_graph()
    variables = VariablesMap(
        global_time_vector=[datetime(2020, 1, 1), datetime(2022, 1, 1)],
        variables={},
    )
    energy_calculator = EnergyCalculator(graph=graph)
    consumer_results = energy_calculator.evaluate_energy_usage(variables)
    emission_results = energy_calculator.evaluate_emissions(
        variables_map=variables,
        consumer_results=consumer_results,
    )
    return get_asset_result(
        GraphResult(
            graph=graph,
            consumer_results=consumer_results,
            variables_map=variables,
            emission_results=emission_results,
        )
    )


def test_is_valid_is_boolean(minimal_asset_result: EcalcModelResult):
    """
    We had a bug where all TimeSeriesBoolean values became floats because of rounding,
    this makes sure that does not happen again.
    """
    assert all(type(value) is bool for value in minimal_asset_result.component_result.is_valid.values)
