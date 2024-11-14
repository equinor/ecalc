import pytest

from libecalc.application.energy_calculator import EnergyCalculator
from libecalc.application.graph_result import EnergyCalculatorResult
from libecalc.fixtures import YamlCase


@pytest.fixture
def result(all_energy_usage_models_yaml: YamlCase) -> EnergyCalculatorResult:
    model = all_energy_usage_models_yaml.get_yaml_model()
    model.validate_for_run()
    energy_calculator = EnergyCalculator(energy_model=model, expression_evaluator=model.variables)
    variables = model.variables
    consumer_results = energy_calculator.evaluate_energy_usage()
    emission_results = energy_calculator.evaluate_emissions()

    return EnergyCalculatorResult(
        consumer_results=consumer_results,
        variables_map=variables,
        emission_results=emission_results,
    )


@pytest.mark.snapshot
def test_all_results(result, rounded_snapshot):
    snapshot_name = "all_energy_usage_models_v3.json"
    data = result.model_dump()
    rounded_snapshot(data=data, snapshot_name=snapshot_name)
