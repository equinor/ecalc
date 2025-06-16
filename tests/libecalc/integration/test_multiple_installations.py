from datetime import datetime

import pytest

from libecalc.common.time_utils import Frequency
from libecalc.common.units import Unit
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
        configuration=yaml_asset_configuration_service_factory(
            asset, "multiple_installations_asset"
        ).get_configuration(),
        resource_service=resource_service_factory({}),
        output_frequency=Frequency.YEAR,
    )


def test_asset_with_multiple_installations(model_with_two_installations):
    model_with_two_installations.evaluate_energy_usage()
    model_with_two_installations.evaluate_emissions()
    asset_result = get_asset_result(model_with_two_installations.get_graph_result())

    assert len(asset_result.component_result.energy_usage.periods) == 3
    assert asset_result.component_result.energy_usage.values == [150, 150, 150]
    assert asset_result.component_result.energy_usage.unit == Unit.STANDARD_CUBIC_METER_PER_DAY

    emission_result = asset_result.component_result.emissions["co2"]
    assert emission_result.rate.values == pytest.approx([0.3, 0.3, 0.3], rel=10e-6)
    assert emission_result.rate.unit == Unit.TONS_PER_DAY
