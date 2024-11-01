import json
from io import StringIO
from pathlib import Path
from typing import cast

import pytest
import yaml

from libecalc.common.math.numbers import Numbers
from libecalc.examples import advanced, simple
from libecalc.fixtures import YamlCase
from libecalc.fixtures.cases import (
    all_energy_usage_models,
    consumer_system_v2,
    ltp_export,
)
from libecalc.presentation.yaml.configuration_service import ConfigurationService
from libecalc.presentation.yaml.yaml_entities import ResourceStream
from libecalc.presentation.yaml.yaml_models.yaml_model import ReaderType, YamlConfiguration, YamlValidator
from libecalc.presentation.yaml.yaml_types.components.yaml_asset import YamlAsset
from tests.libecalc.yaml_builder import (
    YamlAssetBuilder,
    YamlEnergyUsageModelDirectBuilder,
    YamlFuelConsumerBuilder,
    YamlInstallationBuilder,
)


def _round_floats(obj):
    if isinstance(obj, float):
        return float(Numbers.format_to_precision(obj, precision=8))
    elif isinstance(obj, dict):
        return {k: _round_floats(v) for k, v in obj.items()}
    elif isinstance(obj, list | tuple):
        return [_round_floats(v) for v in obj]
    return obj


@pytest.fixture
def rounded_snapshot(snapshot):
    def rounded_snapshot(data: dict, snapshot_name: str):
        snapshot.assert_match(
            json.dumps(_round_floats(data), sort_keys=True, indent=4, default=str), snapshot_name=snapshot_name
        )

    return rounded_snapshot


valid_example_cases = {
    "simple": (Path(simple.__file__).parent / "model.yaml").absolute(),
    "simple_temporal": (Path(simple.__file__).parent / "model_temporal.yaml").absolute(),
    "advanced": (Path(advanced.__file__).parent / "model.yaml").absolute(),
    "ltp": (Path(ltp_export.__file__).parent / "data" / "ltp_export.yaml").absolute(),
    "all_energy_usage_models": (
        Path(all_energy_usage_models.__file__).parent / "data" / "all_energy_usage_models.yaml"
    ).absolute(),
    "consumer_system_v2": (Path(consumer_system_v2.__file__).parent / "data" / "consumer_system_v2.yaml").absolute(),
}

# The value should be the name of a fixture returning the YamlCase for the example
valid_example_yaml_case_fixture_names = {
    "simple": "simple_yaml",
    "simple_temporal": "simple_temporal_yaml",
    "advanced": "advanced_yaml",
    "ltp": "ltp_export_yaml",
    "all_energy_usage_models": "all_energy_usage_models_yaml",
    "consumer_system_v2": "consumer_system_v2_yaml",
}

invalid_example_cases = {
    "simple_duplicate_names": (Path(simple.__file__).parent / "model_duplicate_names.yaml").absolute(),
    "simple_multiple_energy_models_one_consumer": (
        Path(simple.__file__).parent / "model_multiple_energy_models_one_consumer.yaml"
    ).absolute(),
    "simple_duplicate_emissions_in_fuel": (
        Path(simple.__file__).parent / "model_duplicate_emissions_in_fuel.yaml"
    ).absolute(),
}


@pytest.fixture(scope="session")
def simple_yaml_path():
    return valid_example_cases["simple"]


@pytest.fixture(scope="session")
def simple_temporal_yaml_path():
    return valid_example_cases["simple_temporal"]


@pytest.fixture(scope="session")
def simple_duplicate_names_yaml_path():
    return invalid_example_cases["simple_duplicate_names"]


@pytest.fixture(scope="session")
def simple_multiple_energy_models_yaml_path():
    return invalid_example_cases["simple_multiple_energy_models_one_consumer"]


@pytest.fixture(scope="session")
def simple_duplicate_emissions_yaml_path():
    return invalid_example_cases["simple_duplicate_emissions_in_fuel"]


@pytest.fixture(scope="session")
def advanced_yaml_path():
    return valid_example_cases["advanced"]


@pytest.fixture
def ltp_yaml_path():
    return valid_example_cases["ltp"]


@pytest.fixture(
    scope="function", params=list(valid_example_yaml_case_fixture_names.items()), ids=lambda param: param[0]
)
def valid_example_case_yaml_case(request) -> YamlCase:
    """
    Parametrized fixture returning each YamlCase for all valid examples
    """
    yaml_case = request.getfixturevalue(request.param[1])
    return yaml_case


class YamlAssetConfigurationService(ConfigurationService):
    def __init__(self, model: YamlAsset, name: str):
        self._name = name
        self._model = model
        self._source = None

    @property
    def name(self):
        return self._name

    @property
    def source(self):
        return self.get_yaml()

    def get_yaml(self) -> str:
        if self._source is not None:
            return self._source
        data = self._model.model_dump(by_alias=True, exclude_unset=True, mode="json")
        return yaml.dump(data)

    def get_configuration(self) -> YamlValidator:
        stream = ResourceStream(name=self._name, stream=StringIO(self.get_yaml()))
        main_yaml_model = YamlConfiguration.Builder.get_yaml_reader(ReaderType.PYYAML).read(
            main_yaml=stream,
            enable_include=True,
        )
        return cast(YamlValidator, main_yaml_model)


@pytest.fixture
def yaml_asset_configuration_service_factory():
    def yaml_asset_configuration_service(model: YamlAsset, name: str):
        return YamlAssetConfigurationService(model=model, name=name)

    return yaml_asset_configuration_service


@pytest.fixture
def yaml_asset_builder_factory():
    return lambda: YamlAssetBuilder()


@pytest.fixture
def yaml_installation_builder_factory():
    return lambda: YamlInstallationBuilder()


@pytest.fixture
def minimal_installation_yaml_factory(yaml_installation_builder_factory):
    def minimal_installation_yaml(
        name: str = "DefaultInstallation",
        consumer_name: str = "flare",
        fuel_name: str = "fuel",
        fuel_rate: int | str = 50,
    ):
        return (
            yaml_installation_builder_factory()
            .with_test_data()
            .with_name(name)
            .with_fuel_consumers(
                [
                    YamlFuelConsumerBuilder()
                    .with_test_data()
                    .with_name(consumer_name)
                    .with_fuel(fuel_name)
                    .with_energy_usage_model(
                        YamlEnergyUsageModelDirectBuilder().with_test_data().with_fuel_rate(fuel_rate).build()
                    )
                    .build()
                ]
            )
            .build()
        )

    return minimal_installation_yaml


@pytest.fixture
def minimal_model_yaml_factory(minimal_installation_yaml_factory):
    def minimal_model_yaml(fuel_rate: int | str = 50):
        fuel_name = "fuel"
        installation = minimal_installation_yaml_factory(fuel_name="fuel", fuel_rate=fuel_rate)
        model = (
            YamlAssetBuilder()
            .with_test_data(fuel_name=fuel_name)
            .with_installations([installation])
            .with_start("2020-01-01")
            .with_end("2023-01-01")
        )
        return YamlAssetConfigurationService(model.build(), name="minimal_model")

    return minimal_model_yaml
