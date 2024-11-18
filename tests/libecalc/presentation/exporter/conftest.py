import pytest
from datetime import datetime
from io import StringIO
from typing import cast, Optional, Union
from pathlib import Path
import numpy as np

from libecalc.presentation.exporter.dto.dtos import QueryResult

from libecalc.presentation.yaml.resource_service import ResourceService
from libecalc.presentation.json_result.mapper import get_asset_result
from libecalc.common.units import Unit
from libecalc.common.variables import VariablesMap
from libecalc.application.energy_calculator import EnergyCalculator
from libecalc.presentation.exporter.dto.dtos import FilteredResult
from libecalc.application.graph_result import GraphResult
from libecalc.presentation.exporter.infrastructure import ExportableGraphResult
from libecalc.presentation.exporter.configs.configs import LTPConfig
from libecalc.common.time_utils import Period
from libecalc.presentation.yaml.yaml_types.time_series.yaml_time_series import YamlTimeSeriesCollection
from libecalc.testing.yaml_builder import (
    YamlFuelTypeBuilder,
    YamlFuelConsumerBuilder,
    YamlInstallationBuilder,
    YamlEnergyUsageModelDirectBuilder,
    YamlAssetBuilder,
    YamlElectricityConsumerBuilder,
)
from ecalc_cli.infrastructure.file_resource_service import FileResourceService
from libecalc.dto.types import (
    FuelTypeUserDefinedCategoryType,
    ConsumerUserDefinedCategoryType,
    InstallationUserDefinedCategoryType,
)
from libecalc.presentation.yaml.yaml_types.components.yaml_asset import YamlAsset
from libecalc.presentation.yaml.yaml_types.facility_model.yaml_facility_model import YamlFacilityModel
from libecalc.presentation.yaml.yaml_types.components.yaml_installation import YamlInstallation
from libecalc.presentation.yaml.yaml_types.components.legacy.energy_usage_model.yaml_energy_usage_model_direct import (
    ConsumptionRateType,
)
from libecalc.presentation.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel
from libecalc.presentation.yaml.yaml_entities import ResourceStream, MemoryResource
from libecalc.presentation.yaml.configuration_service import ConfigurationService
from libecalc.presentation.yaml.yaml_models.yaml_model import ReaderType, YamlConfiguration, YamlValidator
from libecalc.common.time_utils import Frequency, Periods
from libecalc.presentation.yaml.model import YamlModel
from libecalc.expression import Expression
from libecalc.presentation.yaml.yaml_types.fuel_type.yaml_fuel_type import YamlFuelType

date1 = datetime(2027, 1, 1)
date2 = datetime(2027, 4, 10)
date3 = datetime(2028, 1, 1)
date4 = datetime(2028, 4, 10)
date5 = datetime(2029, 1, 1)

time_vector_installation = [
    date1,
    date2,
    date3,
    date4,
    date5,
]

period1 = Period(date1, date2)
period2 = Period(date2, date3)
period3 = Period(date3, date4)
period4 = Period(date4, date5)
period5 = Period(date5)

full_period = Period(datetime(1900, 1, 1))
period_from_date1 = Period(date1)
period_from_date3 = Period(date3)

days_year1_first_half = period1.duration.days
days_year2_first_half = period3.duration.days

days_year1_second_half = period2.duration.days
days_year2_second_half = period4.duration.days

regularity_installation = 1.0
regularity_consumer = 1.0

regularity_temporal_installation = {full_period: Expression.setup_from_expression(regularity_installation)}
regularity_temporal_consumer = {full_period: Expression.setup_from_expression(regularity_consumer)}

fuel_rate = 67000
diesel_rate = 120000

co2_factor = 1
ch4_factor = 0.1
nox_factor = 0.5
nmvoc_factor = 0


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


# LTP specific methods:
def get_consumption(
    model: Union[YamlInstallation, YamlAsset, YamlModel],
    variables_map: VariablesMap,
    frequency: Frequency,
    periods: Periods,
) -> FilteredResult:
    energy_calculator = EnergyCalculator(graph=model.get_graph())
    precision = 6

    consumer_results = energy_calculator.evaluate_energy_usage(variables_map)
    emission_results = energy_calculator.evaluate_emissions(
        variables_map=variables_map,
        consumer_results=consumer_results,
    )

    graph_result = GraphResult(
        graph=model.get_graph(),
        variables_map=variables_map,
        consumer_results=consumer_results,
        emission_results=emission_results,
    )

    ltp_filter = LTPConfig.filter(frequency=frequency)
    ltp_result = ltp_filter.filter(ExportableGraphResult(graph_result), periods)

    return ltp_result


def get_sum_ltp_column(ltp_result: FilteredResult, installation_nr, ltp_column: str) -> float:
    installation_query_results = ltp_result.query_results[installation_nr].query_results
    column = [column for column in installation_query_results if column.id == ltp_column][0]

    ltp_sum = sum(float(v) for (k, v) in column.values.items())
    return ltp_sum


def get_ltp_column(ltp_result: FilteredResult, installation_nr, ltp_column: str) -> QueryResult:
    installation_query_results = ltp_result.query_results[installation_nr].query_results
    column = [column for column in installation_query_results if column.id == ltp_column][0]

    return column


def expected_boiler_fuel_consumption() -> float:
    n_days = np.sum([days_year1_first_half, days_year1_second_half, days_year2_first_half])
    consumption = float(fuel_rate * n_days * regularity_consumer)
    return consumption


def expected_heater_fuel_consumption() -> float:
    n_days = np.sum(days_year2_second_half)
    consumption = float(fuel_rate * n_days * regularity_consumer)
    return consumption


def expected_co2_from_boiler() -> float:
    emission_kg_per_day = float(fuel_rate * co2_factor)
    emission_tons_per_day = Unit.KILO_PER_DAY.to(Unit.TONS_PER_DAY)(emission_kg_per_day)
    n_days = np.sum([days_year1_first_half, days_year1_second_half, days_year2_first_half])
    emission_tons = float(emission_tons_per_day * n_days * regularity_consumer)
    return emission_tons


def expected_co2_from_heater() -> float:
    emission_kg_per_day = float(fuel_rate * co2_factor)
    emission_tons_per_day = Unit.KILO_PER_DAY.to(Unit.TONS_PER_DAY)(emission_kg_per_day)
    n_days = np.sum(days_year2_second_half)
    emission_tons = float(emission_tons_per_day * n_days * regularity_consumer)
    return emission_tons


# General methods:
def calculate_asset_result(
    model: YamlModel,
    variables: VariablesMap,
):
    model = model
    graph = model.get_graph()
    energy_calculator = EnergyCalculator(graph=graph)

    consumer_results = energy_calculator.evaluate_energy_usage(variables)
    emission_results = energy_calculator.evaluate_emissions(variables, consumer_results)

    results_core = GraphResult(
        graph=graph,
        variables_map=variables,
        consumer_results=consumer_results,
        emission_results=emission_results,
    )

    results_dto = get_asset_result(results_core)

    return results_dto


def get_yaml_model(yaml_string: str, frequency: Frequency, resource_service: Optional[dict[str:MemoryResource]] = None):
    configuration_service = OverridableStreamConfigurationService(
        stream=ResourceStream(name="", stream=StringIO(yaml_string)),
    )
    if resource_service is not None:
        resource_service = resource_service
    else:
        resource_service = FileResourceService(working_directory=Path(""))

    return YamlModel(
        configuration_service=configuration_service,
        resource_service=resource_service,
        output_frequency=frequency,
    ).validate_for_run()


def get_asset_yaml_model(
    installations: [YamlInstallation],
    time_vector: list[datetime],
    frequency: Frequency,
    fuel_types: Optional[list[YamlFuelType]] = None,
    facility_inputs: Optional[list[YamlFacilityModel]] = None,
    resource_service: Optional[ResourceService] = None,
    time_series: Optional[list[YamlTimeSeriesCollection]] = None,
):
    asset = (
        YamlAssetBuilder()
        .with_installations(installations=installations)
        .with_start(time_vector[0])
        .with_end(time_vector[-1])
    )

    if fuel_types is not None:
        asset.fuel_types = fuel_types

    if facility_inputs is not None:
        asset.facility_inputs = facility_inputs

    if time_series is not None:
        asset.time_series = time_series

    asset = asset.validate()

    asset_dict = asset.model_dump(
        serialize_as_any=True,
        mode="json",
        exclude_unset=True,
        by_alias=True,
    )

    asset_yaml_string = PyYamlYamlModel.dump_yaml(yaml_dict=asset_dict)
    asset_yaml_model = get_yaml_model(
        yaml_string=asset_yaml_string, frequency=frequency, resource_service=resource_service
    )

    return asset_yaml_model


# Fixtures based on builders:
@pytest.fixture
def fuel_turbine():
    return (
        YamlFuelTypeBuilder()
        .with_name("fuel_gas")
        .with_emission_names_and_factors(names=["co2"], factors=[co2_factor])
        .with_category(FuelTypeUserDefinedCategoryType.FUEL_GAS)
    ).validate()


@pytest.fixture
def fuel_multi():
    return (
        YamlFuelTypeBuilder()
        .with_name("fuel_gas_multi")
        # .with_emission_names_and_factors(names=["co2", "ch4", "nmvoc", "nox"], factors=[2, 0.005, 0.002, 0.001])
        .with_emission_names_and_factors(
            names=["co2", "ch4", "nmvoc", "nox"], factors=[co2_factor, ch4_factor, nmvoc_factor, nox_factor]
        )
        .with_category(FuelTypeUserDefinedCategoryType.FUEL_GAS)
    ).validate()


@pytest.fixture
def energy_usage_model_direct():
    def energy_usage_model(rate: float):
        return (
            YamlEnergyUsageModelDirectBuilder()
            .with_fuel_rate(rate)
            .with_consumption_rate_type(ConsumptionRateType.STREAM_DAY)
        ).validate()

    return energy_usage_model


@pytest.fixture
def energy_usage_model_direct_load():
    def energy_usage_model(load: float):
        return (
            YamlEnergyUsageModelDirectBuilder()
            .with_load(load)
            .with_consumption_rate_type(ConsumptionRateType.STREAM_DAY)
        ).validate()

    return energy_usage_model


@pytest.fixture
def fuel_consumer_direct(energy_usage_model_direct):
    def fuel_consumer(fuel_reference_name: str, rate: float):
        return (
            YamlFuelConsumerBuilder()
            .with_name("fuel_consumer")
            .with_fuel(fuel_reference_name)
            .with_category(ConsumerUserDefinedCategoryType.FLARE)
            .with_energy_usage_model(energy_usage_model_direct(rate))
        ).validate()

    return fuel_consumer


@pytest.fixture
def fuel_consumer_direct_load(energy_usage_model_direct_load):
    def fuel_consumer(fuel_reference_name: str, load: float):
        return (
            YamlFuelConsumerBuilder()
            .with_name("fuel_consumer")
            .with_fuel(fuel_reference_name)
            .with_category(ConsumerUserDefinedCategoryType.BASE_LOAD)
            .with_energy_usage_model(energy_usage_model_direct_load(load))
        ).validate()

    return fuel_consumer


@pytest.fixture
def el_consumer_direct_base_load(energy_usage_model_direct_load):
    def el_consumer(el_reference_name: str, load: float):
        return (
            YamlElectricityConsumerBuilder()
            .with_name(el_reference_name)
            .with_category(ConsumerUserDefinedCategoryType.BASE_LOAD)
            .with_energy_usage_model(energy_usage_model_direct_load(load))
        ).validate()

    return el_consumer


@pytest.fixture
def installation_boiler_heater(fuel_turbine):
    energy_usage_model = (
        YamlEnergyUsageModelDirectBuilder()
        .with_fuel_rate(fuel_rate)
        .with_consumption_rate_type(ConsumptionRateType.STREAM_DAY)
    ).validate()

    fuel_consumer = (
        YamlFuelConsumerBuilder()
        .with_name("boiler")
        .with_fuel(fuel_turbine.name)
        .with_energy_usage_model({full_period.start: energy_usage_model})
        .with_category(
            {
                Period(date1, date4).start: ConsumerUserDefinedCategoryType.BOILER,
                Period(date4).start: ConsumerUserDefinedCategoryType.HEATER,
            }
        )
    ).validate()

    installation = (
        YamlInstallationBuilder()
        .with_name("INSTALLATION A")
        .with_category(InstallationUserDefinedCategoryType.FIXED)
        .with_fuel(fuel_turbine.name)
        .with_fuel_consumers([fuel_consumer])
        .with_regularity(regularity_installation)
    ).validate()
    return installation
