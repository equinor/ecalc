from datetime import datetime

import pytest

from libecalc.application.energy_calculator import EnergyCalculator
from libecalc.application.graph_result import GraphResult
from libecalc.common.time_utils import Frequency
from libecalc.common.units import Unit
from libecalc.common.utils.rates import RateType, TimeSeriesRate
from libecalc.common.variables import VariablesMap
from libecalc.presentation.json_result.mapper import get_asset_result
from libecalc.presentation.yaml.model import YamlModel
from libecalc.presentation.yaml.resource import Resource
from libecalc.presentation.yaml.resource_service import ResourceService
from libecalc.presentation.yaml.yaml_models.yaml_model import YamlValidator


class EmptyResourceService(ResourceService):
    def get_resources(self, configuration: YamlValidator) -> dict[str, Resource]:
        return {}


@pytest.fixture
def model_with_two_installations(
    minimal_installation_yaml_factory, yaml_asset_configuration_service_factory, yaml_asset_builder_factory
) -> YamlModel:
    installation_1 = minimal_installation_yaml_factory(
        name="installation1", fuel_rate=50, fuel_name="fuel", consumer_name="flare1"
    )
    installation_2 = minimal_installation_yaml_factory(
        name="installation2", fuel_rate=100, fuel_name="fuel", consumer_name="flare2"
    )

    asset = (
        yaml_asset_builder_factory()
        .with_test_data(fuel_name="fuel")
        .with_installations([installation_1, installation_2])
        .build()
    )

    return YamlModel(
        configuration_service=yaml_asset_configuration_service_factory(asset, "multiple_installations_asset"),
        resource_service=EmptyResourceService(),
        output_frequency=Frequency.YEAR,
    )


def test_asset_with_multiple_installations(model_with_two_installations):
    graph = model_with_two_installations.get_graph()
    energy_calculator = EnergyCalculator(graph)
    timesteps = [
        datetime(2020, 1, 1),
        datetime(2021, 1, 1),
        datetime(2022, 1, 1),
        datetime(2023, 1, 1),
    ]
    variables_map = VariablesMap(time_vector=timesteps)
    consumer_results = energy_calculator.evaluate_energy_usage(variables_map)
    emission_results = energy_calculator.evaluate_emissions(variables_map, consumer_results)
    graph_result = GraphResult(
        graph=graph,
        variables_map=variables_map,
        consumer_results=consumer_results,
        emission_results=emission_results,
    )

    asset_result = get_asset_result(graph_result)
    assert asset_result.component_result.energy_usage == TimeSeriesRate(
        values=[150, 150, 150],
        unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
        periods=variables_map.get_periods(),
        rate_type=RateType.CALENDAR_DAY,
        regularity=[1.0, 1.0, 1.0],
    )
