import json
from io import StringIO
from pathlib import Path
from typing import Optional, cast, Union


import pytest
import yaml

from libecalc.application.energy_calculator import EnergyCalculator
from libecalc.application.graph_result import GraphResult
from libecalc.common.math.numbers import Numbers
from libecalc.common.time_utils import Frequency, Periods
from libecalc.common.variables import VariablesMap
from libecalc.examples import advanced, simple
from libecalc.fixtures import YamlCase
from libecalc.fixtures.cases import (
    all_energy_usage_models,
    consumer_system_v2,
    ltp_export,
)
from libecalc.presentation.exporter.configs.configs import LTPConfig
from libecalc.presentation.exporter.dto.dtos import FilteredResult, QueryResult
from libecalc.presentation.exporter.infrastructure import ExportableGraphResult
from libecalc.presentation.json_result.mapper import get_asset_result
from libecalc.presentation.yaml.configuration_service import ConfigurationService
from libecalc.presentation.yaml.model import YamlModel
from libecalc.presentation.yaml.resource_service import ResourceService
from libecalc.presentation.yaml.yaml_entities import MemoryResource, ResourceStream
from libecalc.presentation.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel
from libecalc.presentation.yaml.yaml_models.yaml_model import ReaderType, YamlConfiguration, YamlValidator
from libecalc.presentation.yaml.yaml_types.components.yaml_asset import YamlAsset
from libecalc.presentation.yaml.yaml_types.components.yaml_installation import YamlInstallation
from libecalc.testing.dto_energy_model import DTOEnergyModel
from libecalc.testing.yaml_builder import (
    YamlAssetBuilder,
    YamlEnergyUsageModelDirectBuilder,
    YamlFuelConsumerBuilder,
    YamlFuelTypeBuilder,
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


class OverridableStreamConfigurationService(ConfigurationService):
    def __init__(self, stream: ResourceStream, overrides: Optional[dict] = None):
        self._overrides = overrides
        self._stream = stream

    def get_configuration(self) -> YamlValidator:
        main_yaml_model = YamlConfiguration.Builder.get_yaml_reader(ReaderType.PYYAML).read(
            main_yaml=self._stream,
            enable_include=True,
        )

        if self._overrides is not None:
            main_yaml_model._internal_datamodel.update(self._overrides)
        return cast(YamlValidator, main_yaml_model)


@pytest.fixture
def configuration_service_factory():
    def create_configuration_service(
        resource_stream: ResourceStream, overrides: Optional[dict] = None
    ) -> ConfigurationService:
        return OverridableStreamConfigurationService(
            stream=resource_stream,
            overrides=overrides,
        )

    return create_configuration_service


@pytest.fixture
def yaml_asset_configuration_service_factory(configuration_service_factory):
    def yaml_asset_configuration_service(model: YamlAsset, name: str):
        data = model.model_dump(by_alias=True, exclude_unset=True, mode="json")
        source = yaml.dump(data)
        return configuration_service_factory(ResourceStream(stream=StringIO(source), name=name))

    return yaml_asset_configuration_service


@pytest.fixture
def yaml_asset_builder_factory():
    return lambda: YamlAssetBuilder()


class DirectResourceService(ResourceService):
    def __init__(self, resources: dict[str, MemoryResource]):
        self._resources = resources

    def get_resources(self, configuration: YamlValidator) -> dict[str, MemoryResource]:
        return self._resources


@pytest.fixture
def resource_service_factory():
    def create_resource_service(resources: dict[str, MemoryResource]) -> ResourceService:
        return DirectResourceService(resources=resources)

    return create_resource_service


@pytest.fixture
def yaml_installation_builder_factory():
    return lambda: YamlInstallationBuilder()


@pytest.fixture
def yaml_fuel_type_builder_factory():
    return lambda: YamlFuelTypeBuilder()


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
                        YamlEnergyUsageModelDirectBuilder().with_test_data().with_fuel_rate(fuel_rate).validate()
                    )
                    .validate()
                ]
            )
            .validate()
        )

    return minimal_installation_yaml


@pytest.fixture
def minimal_model_yaml_factory(
    yaml_asset_builder_factory,
    minimal_installation_yaml_factory,
    yaml_fuel_type_builder_factory,
    yaml_asset_configuration_service_factory,
):
    def minimal_model_yaml(fuel_rate: int | str = 50) -> ConfigurationService:
        fuel_name = "fuel"
        installation = minimal_installation_yaml_factory(fuel_name="fuel", fuel_rate=fuel_rate)
        model = (
            yaml_asset_builder_factory()
            .with_test_data()
            .with_fuel_types([yaml_fuel_type_builder_factory().with_test_data().with_name(fuel_name).validate()])
            .with_installations([installation])
            .with_start("2020-01-01")
            .with_end("2023-01-01")
        )
        return yaml_asset_configuration_service_factory(model.validate(), name="minimal_model")

    return minimal_model_yaml


@pytest.fixture
def yaml_model_factory(configuration_service_factory, resource_service_factory):
    def create_yaml_model(
        resource_stream: ResourceStream, resources: dict[str, MemoryResource], frequency: Frequency = Frequency.NONE
    ) -> YamlModel:
        return YamlModel(
            configuration_service=configuration_service_factory(resource_stream),
            resource_service=resource_service_factory(resources),
            output_frequency=frequency,
        )

    return create_yaml_model


@pytest.fixture
def energy_model_from_dto_factory():
    """
    Temporary fixture to make it possible to run dtos while making the transition to (energy?) domain models.
    """

    def create_energy_model(component) -> DTOEnergyModel:
        return DTOEnergyModel(component)

    return create_energy_model


class LtpFunctions:
    def get_yaml_model(
        self,
        request,
        asset: YamlAsset,
        resources: dict[str, MemoryResource],
        frequency: Frequency = Frequency.NONE,
    ) -> YamlModel:
        yaml_model_factory = request.getfixturevalue("yaml_model_factory")
        asset_dict = asset.model_dump(
            serialize_as_any=True,
            mode="json",
            exclude_unset=True,
            by_alias=True,
        )

        yaml_string = PyYamlYamlModel.dump_yaml(yaml_dict=asset_dict)
        stream = ResourceStream(name="", stream=StringIO(yaml_string))

        return yaml_model_factory(resource_stream=stream, resources=resources, frequency=frequency)

    def get_consumption(
        self,
        model: Union[YamlInstallation, YamlAsset, YamlModel],
        variables: VariablesMap,
        frequency: Frequency,
        periods: Periods,
    ) -> FilteredResult:
        energy_calculator = EnergyCalculator(energy_model=model, expression_evaluator=variables)

        consumer_results = energy_calculator.evaluate_energy_usage()
        emission_results = energy_calculator.evaluate_emissions()

        graph_result = GraphResult(
            graph=model.get_graph(),
            variables_map=variables,
            consumer_results=consumer_results,
            emission_results=emission_results,
        )

        ltp_filter = LTPConfig.filter(frequency=frequency)
        ltp_result = ltp_filter.filter(ExportableGraphResult(graph_result), periods)

        return ltp_result

    def get_sum_ltp_column(self, ltp_result: FilteredResult, installation_nr, ltp_column: str) -> float:
        installation_query_results = ltp_result.query_results[installation_nr].query_results
        column = [column for column in installation_query_results if column.id == ltp_column][0]

        ltp_sum = sum(float(v) for (k, v) in column.values.items())
        return ltp_sum

    def get_ltp_column(self, ltp_result: FilteredResult, installation_nr, ltp_column: str) -> QueryResult:
        installation_query_results = ltp_result.query_results[installation_nr].query_results
        column = [column for column in installation_query_results if column.id == ltp_column][0]

        return column

    def get_ltp_result(self, model, variables, frequency=Frequency.YEAR):
        return self.get_consumption(
            model=model, variables=variables, periods=variables.get_periods(), frequency=frequency
        )

    def create_variables_map(self, time_vector, rate_values=None):
        variables = {"RATE": rate_values} if rate_values else {}
        return VariablesMap(time_vector=time_vector, variables=variables)

    def calculate_asset_result(self, model: YamlModel, variables: VariablesMap):
        model = model
        graph = model.get_graph()
        energy_calculator = EnergyCalculator(energy_model=model, expression_evaluator=variables)

        consumer_results = energy_calculator.evaluate_energy_usage()
        emission_results = energy_calculator.evaluate_emissions()

        results_core = GraphResult(
            graph=graph,
            variables_map=variables,
            consumer_results=consumer_results,
            emission_results=emission_results,
        )

        results_dto = get_asset_result(results_core)

        return results_dto

    def assert_emissions(self, ltp_result, installation_nr, ltp_column, expected_value):
        actual_value = self.get_sum_ltp_column(ltp_result, installation_nr, ltp_column)
        assert actual_value == pytest.approx(expected_value, 0.00001)

    def assert_consumption(self, ltp_result, installation_nr, ltp_column, expected_value):
        actual_value = self.get_sum_ltp_column(ltp_result, installation_nr, ltp_column)
        assert actual_value == pytest.approx(expected_value, 0.00001)


@pytest.fixture(scope="session")
def ltp_functions():
    return LtpFunctions()
