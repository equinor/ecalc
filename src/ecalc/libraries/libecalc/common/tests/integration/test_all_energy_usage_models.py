import pytest
from libecalc.core.ecalc import EnergyCalculator
from libecalc.core.graph_result import EnergyCalculatorResult, GraphResult


@pytest.fixture
def result(all_energy_usage_models_dto) -> EnergyCalculatorResult:
    ecalc_model = all_energy_usage_models_dto.ecalc_model
    variables = all_energy_usage_models_dto.variables

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

    return result


@pytest.mark.snapshot
def test_all_results(result, rounded_snapshot):
    snapshot_name = "all_energy_usage_models_v3.json"
    rounded_snapshot(data=result.dict(), snapshot_name=snapshot_name)
