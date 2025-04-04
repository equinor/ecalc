import pytest

from libecalc.application.energy_calculator import EnergyCalculator
from libecalc.application.graph_result import GraphResult
from libecalc.fixtures import YamlCase
from libecalc.presentation.json_result.mapper import get_asset_result


@pytest.fixture
def graph_result(all_energy_usage_models_yaml: YamlCase) -> GraphResult:
    model = all_energy_usage_models_yaml.get_yaml_model()
    model.validate_for_run()
    energy_calculator = EnergyCalculator(energy_model=model, expression_evaluator=model.variables)
    variables = model.variables
    consumer_results = energy_calculator.evaluate_energy_usage()
    emission_results = energy_calculator.evaluate_emissions()

    return GraphResult(
        graph=model.get_graph(),
        consumer_results=consumer_results,
        variables_map=variables,
        emission_results=emission_results,
    )


@pytest.mark.snapshot
def test_all_results(graph_result, rounded_snapshot):
    snapshot_name = "all_energy_usage_models_v3.json"

    asset_result = get_asset_result(graph_result).model_dump()
    rounded_snapshot(data=asset_result, snapshot_name=snapshot_name)
