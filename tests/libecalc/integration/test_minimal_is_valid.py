import pytest

from libecalc.application.energy_calculator import EnergyCalculator
from libecalc.application.graph_result import GraphResult
from libecalc.common.time_utils import Frequency
from libecalc.presentation.json_result.mapper import get_asset_result
from libecalc.presentation.json_result.result import EcalcModelResult
from libecalc.presentation.yaml.model import YamlModel


@pytest.fixture
def minimal_asset_result(minimal_model_yaml_factory, resource_service_factory):
    minimal_configuration_service = minimal_model_yaml_factory()
    model = YamlModel(
        configuration_service=minimal_configuration_service,
        resource_service=resource_service_factory({}),
        output_frequency=Frequency.NONE,
    )
    variables = model.variables
    energy_calculator = EnergyCalculator(energy_model=model, expression_evaluator=variables)
    consumer_results = energy_calculator.evaluate_energy_usage()
    emission_results = energy_calculator.evaluate_emissions()
    include_emission_intensity = model._output_frequency == Frequency.YEAR

    return get_asset_result(
        GraphResult(
            graph=model.get_graph(),
            consumer_results=consumer_results,
            variables_map=model.variables,
            emission_results=emission_results,
        ),
        include_emission_intensity,
    )


def test_is_valid_is_boolean(minimal_asset_result: EcalcModelResult):
    """
    We had a bug where all TimeSeriesBoolean values became floats because of rounding,
    this makes sure that does not happen again.
    """
    assert all(type(value) is bool for value in minimal_asset_result.component_result.is_valid.values)
