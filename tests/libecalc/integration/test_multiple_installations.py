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


@pytest.fixture
def model_with_two_installations(
    minimal_installation_yaml_factory,
    yaml_asset_configuration_service_factory,
    yaml_asset_builder_factory,
    yaml_fuel_type_builder_factory,
    resource_service_factory,
) -> YamlModel:
    fuel_name = "fuel"
    installation_1 = minimal_installation_yaml_factory(
        name="installation1", fuel_rate=50, fuel_name=fuel_name, consumer_name="flare1"
    )
    installation_2 = minimal_installation_yaml_factory(
        name="installation2", fuel_rate=100, fuel_name=fuel_name, consumer_name="flare2"
    )

    asset = (
        yaml_asset_builder_factory()
        .with_test_data()
        .with_fuel_types([yaml_fuel_type_builder_factory().with_test_data().with_name(fuel_name).validate()])
        .with_installations([installation_1, installation_2])
        .with_start(datetime(2020, 1, 1))
        .with_end(datetime(2023, 1, 1))
        .validate()
    )

    return YamlModel(
        configuration_service=yaml_asset_configuration_service_factory(asset, "multiple_installations_asset"),
        resource_service=resource_service_factory({}),
        output_frequency=Frequency.YEAR,
    )


def test_asset_with_multiple_installations(model_with_two_installations):
    timesteps = [
        datetime(2020, 1, 1),
        datetime(2021, 1, 1),
        datetime(2022, 1, 1),
        datetime(2023, 1, 1),
    ]
    variables_map = VariablesMap(time_vector=timesteps)
    energy_calculator = EnergyCalculator(energy_model=model_with_two_installations, expression_evaluator=variables_map)
    consumer_results = energy_calculator.evaluate_energy_usage()
    emission_results = energy_calculator.evaluate_emissions()
    graph_result = GraphResult(
        graph=model_with_two_installations.get_graph(),
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
