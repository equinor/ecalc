import json
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import cast

import pytest
import yaml

from ecalc_neqsim_wrapper import NeqsimService
from libecalc.common.math.numbers import Numbers
from libecalc.common.time_utils import Frequency, Period, Periods
from libecalc.common.utils.rates import RateType
from libecalc.common.variables import ExpressionEvaluator, VariablesMap
from libecalc.domain.regularity import Regularity
from libecalc.domain.resource import Resource
from libecalc.examples import advanced, drogon, simple
from libecalc.expression.expression import ExpressionType
from libecalc.fixtures import YamlCase
from libecalc.fixtures.cases import all_energy_usage_models, ltp_export
from libecalc.presentation.yaml.configuration_service import ConfigurationService
from libecalc.presentation.yaml.domain.expression_time_series_flow_rate import ExpressionTimeSeriesFlowRate
from libecalc.presentation.yaml.domain.expression_time_series_fluid_density import ExpressionTimeSeriesFluidDensity
from libecalc.presentation.yaml.domain.expression_time_series_power import ExpressionTimeSeriesPower
from libecalc.presentation.yaml.domain.expression_time_series_pressure import ExpressionTimeSeriesPressure
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression
from libecalc.presentation.yaml.domain.time_series_resource import TimeSeriesResource
from libecalc.presentation.yaml.model import YamlModel
from libecalc.presentation.yaml.resource_service import ResourceService, TupleWithError
from libecalc.presentation.yaml.yaml_entities import MemoryResource, ResourceStream
from libecalc.presentation.yaml.yaml_models.yaml_model import ReaderType, YamlConfiguration, YamlValidator
from libecalc.presentation.yaml.yaml_types.components.yaml_asset import YamlAsset
from libecalc.testing.dto_energy_model import DTOEnergyModel
from libecalc.testing.yaml_builder import (
    YamlAssetBuilder,
    YamlElectricityConsumerBuilder,
    YamlEnergyUsageModelDirectFuelBuilder,
    YamlFuelConsumerBuilder,
    YamlFuelTypeBuilder,
    YamlGeneratorSetBuilder,
    YamlInstallationBuilder,
    YamlTimeSeriesBuilder,
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
    "drogon": (Path(drogon.__file__).parent / "model.yaml").absolute(),
    "ltp": (Path(ltp_export.__file__).parent / "data" / "ltp_export.yaml").absolute(),
    "all_energy_usage_models": (
        Path(all_energy_usage_models.__file__).parent / "data" / "all_energy_usage_models.yaml"
    ).absolute(),
}

# The value should be the name of a fixture returning the YamlCase for the example
valid_example_yaml_case_fixture_names = {
    "simple": "simple_yaml",
    "simple_temporal": "simple_temporal_yaml",
    "advanced": "advanced_yaml",
    "drogon": "drogon_yaml",
    "ltp": "ltp_export_yaml",
    "all_energy_usage_models": "all_energy_usage_models_yaml",
}

invalid_example_cases = {
    "simple_multiple_energy_models_one_consumer": (
        Path(simple.__file__).parent / "model_multiple_energy_models_one_consumer.yaml"
    ).absolute(),
}


@pytest.fixture(scope="session")
def simple_yaml_path():
    return valid_example_cases["simple"]


@pytest.fixture(scope="session")
def simple_temporal_yaml_path():
    return valid_example_cases["simple_temporal"]


@pytest.fixture(scope="session")
def simple_multiple_energy_models_yaml_path():
    return invalid_example_cases["simple_multiple_energy_models_one_consumer"]


@pytest.fixture(scope="session")
def advanced_yaml_path():
    return valid_example_cases["advanced"]


@pytest.fixture(scope="session")
def drogon_yaml_path():
    return valid_example_cases["drogon"]


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
    def __init__(self, stream: ResourceStream, overrides: dict | None = None):
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
        resource_stream: ResourceStream, overrides: dict | None = None
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


@pytest.fixture
def yaml_time_series_factory():
    return YamlTimeSeriesBuilder


class DirectResourceService(ResourceService):
    def __init__(self, resources: dict[str, MemoryResource | TimeSeriesResource]):
        self._resources = resources

        self._times_series_resources = {}
        self._facility_resources = {}
        for resource_name, resource in resources.items():
            if isinstance(resource, TimeSeriesResource):
                self._resources[resource_name] = resource
            elif "date" in resource.get_headers() or "DATE" in resource.get_headers():
                self._times_series_resources[resource_name] = TimeSeriesResource(resource)
            else:
                self._facility_resources[resource_name] = resource

    def get_facility_resources(self) -> TupleWithError[dict[str, Resource]]:
        return self._facility_resources, []

    def get_time_series_resources(self) -> TupleWithError[dict[str, TimeSeriesResource]]:
        return self._times_series_resources, []


@pytest.fixture
def resource_service_factory():
    def create_resource_service(resources: dict[str, MemoryResource], configuration: YamlValidator) -> ResourceService:
        return DirectResourceService(resources=resources)

    return create_resource_service


@pytest.fixture
def yaml_installation_builder_factory():
    return lambda: YamlInstallationBuilder()


@pytest.fixture
def yaml_fuel_type_builder_factory():
    return lambda: YamlFuelTypeBuilder()


@pytest.fixture
def yaml_generator_set_builder_factory():
    return lambda: YamlGeneratorSetBuilder()


@pytest.fixture
def yaml_fuel_consumer_builder_factory():
    return lambda: YamlFuelConsumerBuilder()


@pytest.fixture
def yaml_electricity_consumer_builder_factory():
    return lambda: YamlElectricityConsumerBuilder()


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
                        YamlEnergyUsageModelDirectFuelBuilder().with_test_data().with_fuel_rate(fuel_rate).validate()
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
    def minimal_model_yaml(fuel_rate: int | str = 50, models: list = None) -> ConfigurationService:
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
        if models:
            model.with_models(models)

        model = model.validate()

        return yaml_asset_configuration_service_factory(model, name="minimal_model")

    return minimal_model_yaml


@pytest.fixture
def yaml_model_factory(configuration_service_factory, resource_service_factory):
    def create_yaml_model(
        configuration: ResourceStream | YamlValidator,
        resources: dict[str, MemoryResource],
        frequency: Frequency = Frequency.NONE,
    ) -> YamlModel:
        if isinstance(configuration, ResourceStream):
            configuration = configuration_service_factory(configuration).get_configuration()

        return YamlModel(
            configuration=configuration,
            resource_service=resource_service_factory(resources, configuration),
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


class ExpressionEvaluatorBuilder:
    def from_periods_obj(self, periods: Periods, variables: dict[str, list[float]] = None):
        return VariablesMap(periods=periods, variables=variables)

    def from_periods(self, periods: list[Period], variables: dict[str, list[float]] = None) -> VariablesMap:
        return VariablesMap(periods=Periods(periods), variables=variables)

    def from_time_vector(self, time_vector: list[datetime], variables: dict[str, list[float]] = None) -> VariablesMap:
        return VariablesMap(
            periods=Periods.create_periods(time_vector, include_before=False, include_after=False), variables=variables
        )


@pytest.fixture
def expression_evaluator_factory() -> ExpressionEvaluatorBuilder:
    return ExpressionEvaluatorBuilder()


@pytest.fixture(scope="function", autouse=True)
def with_neqsim_service():
    neqsim_service = NeqsimService.factory(use_jpype=True)
    yield neqsim_service


@pytest.fixture(scope="session", autouse=True)
def shutdown_neqsim_service():
    yield None
    NeqsimService.factory(use_jpype=True).shutdown()


@pytest.fixture
def make_time_series_flow_rate():
    def _make_time_series_flow_rate(
        value: float,
        evaluator: ExpressionEvaluator,
        regularity: Regularity,
        rate_type: RateType | None = None,
        condition_expression: ExpressionType | None = None,
    ) -> ExpressionTimeSeriesFlowRate:
        if rate_type is None:
            rate_type = RateType.CALENDAR_DAY

        return ExpressionTimeSeriesFlowRate(
            time_series_expression=TimeSeriesExpression(
                expression=value, expression_evaluator=evaluator, condition=condition_expression
            ),
            regularity=regularity,
            consumption_rate_type=rate_type,
        )

    return _make_time_series_flow_rate


@pytest.fixture
def make_time_series_power():
    def _make_time_series_power(
        value: float,
        evaluator: ExpressionEvaluator,
        regularity: Regularity,
        rate_type: RateType | None = None,
        condition_expression: ExpressionType | None = None,
    ) -> ExpressionTimeSeriesPower:
        if rate_type is None:
            rate_type = RateType.CALENDAR_DAY

        return ExpressionTimeSeriesPower(
            time_series_expression=TimeSeriesExpression(
                expression=value, expression_evaluator=evaluator, condition=condition_expression
            ),
            regularity=regularity,
            consumption_rate_type=rate_type,
        )

    return _make_time_series_power


@pytest.fixture
def make_time_series_pressure():
    def _make_time_series_pressure(value: float, evaluator: ExpressionEvaluator) -> ExpressionTimeSeriesPressure:
        return ExpressionTimeSeriesPressure(
            time_series_expression=TimeSeriesExpression(expression=value, expression_evaluator=evaluator),
        )

    return _make_time_series_pressure


@pytest.fixture
def make_time_series_fluid_density():
    def _make_time_series_fluid_density(
        value: float, evaluator: ExpressionEvaluator
    ) -> ExpressionTimeSeriesFluidDensity:
        return ExpressionTimeSeriesFluidDensity(
            time_series_expression=TimeSeriesExpression(expression=value, expression_evaluator=evaluator),
        )

    return _make_time_series_fluid_density
