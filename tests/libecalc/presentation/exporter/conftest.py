import pytest
from datetime import datetime
from io import StringIO
from typing import cast, Optional, Union
from pathlib import Path
import numpy as np
import pandas as pd
from copy import deepcopy

from libecalc.presentation.exporter.dto.dtos import QueryResult

from libecalc.presentation.yaml.domain.reference_service import ReferenceService
from libecalc.presentation.yaml.resource_service import ResourceService
from libecalc.presentation.json_result.mapper import get_asset_result
from libecalc.presentation.json_result.result import EcalcModelResult
from libecalc.common.units import Unit
from libecalc.common.utils.rates import RateType
from libecalc.common.variables import VariablesMap
from libecalc.application.energy_calculator import EnergyCalculator
from libecalc.presentation.exporter.dto.dtos import FilteredResult
from libecalc.application.graph_result import GraphResult
from libecalc.presentation.exporter.infrastructure import ExportableGraphResult
from libecalc.presentation.exporter.configs.configs import LTPConfig
from libecalc.common.time_utils import Period, calculate_delta_days
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_types.time_series.yaml_time_series import YamlTimeSeriesCollection
from libecalc.testing.yaml_builder import (
    YamlFuelTypeBuilder,
    YamlFuelConsumerBuilder,
    YamlInstallationBuilder,
    YamlEnergyUsageModelDirectBuilder,
    YamlAssetBuilder,
    YamlVentingEmitterDirectTypeBuilder,
    YamlGeneratorSetBuilder,
    YamlElectricity2fuelBuilder,
    YamlElectricityConsumerBuilder,
    YamlTimeSeriesBuilder,
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
from libecalc.presentation.yaml.yaml_types.yaml_stream_conditions import (
    YamlEmissionRateUnits,
)
from libecalc.presentation.yaml.yaml_types.fuel_type.yaml_fuel_type import YamlFuelType
from tests.conftest import resource_service_factory

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


@pytest.fixture
def generator_electricity2fuel_17MW_resource():
    return MemoryResource(
        data=[
            [0, 0.1, 10, 11, 12, 14, 15, 16, 17, 17.1, 18.5, 20, 20.5, 20.6, 24, 28, 30, 32, 34, 36, 38, 40, 41, 410],
            [
                0,
                75803.4,
                75803.4,
                80759.1,
                85714.8,
                95744,
                100728.8,
                105676.9,
                110598.4,
                136263.4,
                143260,
                151004.1,
                153736.5,
                154084.7,
                171429.6,
                191488,
                201457.5,
                211353.8,
                221196.9,
                231054,
                241049.3,
                251374.6,
                256839.4,
                2568394,
            ],
        ],  # float and int with equal value should count as equal.
        headers=[
            "POWER",
            "FUEL",
        ],
    )


@pytest.fixture
def onshore_power_electricity2fuel_resource():
    return MemoryResource(
        data=[
            [0, 10, 20],
            [0, 0, 0],
        ],  # float and int with equal value should count as equal.
        headers=[
            "POWER",
            "FUEL",
        ],
    )


@pytest.fixture
def cable_loss_time_series_resource():
    return MemoryResource(
        data=[
            [
                "01.01.2021",
                "01.01.2022",
                "01.01.2023",
                "01.01.2024",
                "01.01.2025",
                "01.01.2026",
                "01.01.2027",
                "01.01.2028",
                "01.01.2029",
                "01.01.2030",
            ],
            [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
        ],  # float and int with equal value should count as equal.
        headers=[
            "DATE",
            "CABLE_LOSS_FACTOR",
        ],
    )


def get_sum_ltp_column(ltp_result: FilteredResult, installation_nr, ltp_column: str) -> float:
    installation_query_results = ltp_result.query_results[installation_nr].query_results
    column = [column for column in installation_query_results if column.id == ltp_column][0]

    ltp_sum = sum(float(v) for (k, v) in column.values.items())
    return ltp_sum


def get_ltp_column(ltp_result: FilteredResult, installation_nr, ltp_column: str) -> QueryResult:
    installation_query_results = ltp_result.query_results[installation_nr].query_results
    column = [column for column in installation_query_results if column.id == ltp_column][0]

    return column


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
        .with_emission_names_and_factors(names=["co2", "ch4", "nmvoc", "nox"], factors=[2, 0.005, 0.002, 0.001])
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


def test_boiler_heater_categories(fuel_turbine, installation_boiler_heater):
    variables_map = VariablesMap(time_vector=time_vector_installation, variables={})

    asset = (
        YamlAssetBuilder()
        .with_installations(installations=[installation_boiler_heater])
        .with_fuel_types(fuel_types=[fuel_turbine])
        .with_start(date1)
        .with_end(date5)
    ).validate()

    asset_dict = asset.model_dump(
        serialize_as_any=True,
        mode="json",
        exclude_unset=True,
        by_alias=True,
    )

    asset_yaml_string = PyYamlYamlModel.dump_yaml(yaml_dict=asset_dict)
    asset_yaml_model = get_yaml_model(yaml_string=asset_yaml_string, frequency=Frequency.YEAR)

    ltp_result = get_consumption(
        model=asset_yaml_model,
        variables_map=variables_map,
        frequency=Frequency.YEAR,
        periods=asset_yaml_model.variables.get_periods(),
    )
    boiler_fuel_consumption = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column="boilerFuelGasConsumption")
    heater_fuel_consumption = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column="heaterFuelGasConsumption")
    co2_from_boiler = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column="boilerFuelGasCo2Mass")
    co2_from_heater = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column="heaterFuelGasCo2Mass")

    assert boiler_fuel_consumption == expected_boiler_fuel_consumption()
    assert heater_fuel_consumption == expected_heater_fuel_consumption()
    assert co2_from_boiler == expected_co2_from_boiler()
    assert co2_from_heater == expected_co2_from_heater()


def test_venting_emitter(fuel_consumer_direct, fuel_turbine):
    """Test venting emitters for LTP export.

    Verify correct behaviour if input rate is given in different units and rate types (sd and cd).
    """

    time_vector = [
        datetime(2027, 1, 1),
        datetime(2028, 1, 1),
    ]
    regularity = 0.2
    emission_rate = 10

    variables_map = VariablesMap(time_vector=time_vector, variables={})

    venting_emitter_sd_kg_per_day = (
        YamlVentingEmitterDirectTypeBuilder()
        .with_name("Venting emitter 1")
        .with_category(ConsumerUserDefinedCategoryType.STORAGE)
        .with_emission_names_rates_units_and_types(
            names=["ch4"],
            rates=[emission_rate],
            units=[YamlEmissionRateUnits.KILO_PER_DAY],
            rate_types=[RateType.STREAM_DAY],
        )
    ).validate()

    venting_emitter_sd_tons_per_day = (
        YamlVentingEmitterDirectTypeBuilder()
        .with_name("Venting emitter 1")
        .with_category(ConsumerUserDefinedCategoryType.STORAGE)
        .with_emission_names_rates_units_and_types(
            names=["ch4"],
            rates=[emission_rate],
            units=[YamlEmissionRateUnits.TONS_PER_DAY],
            rate_types=[RateType.STREAM_DAY],
        )
    ).validate()

    venting_emitter_cd_kg_per_day = (
        YamlVentingEmitterDirectTypeBuilder()
        .with_name("Venting emitter 1")
        .with_category(ConsumerUserDefinedCategoryType.STORAGE)
        .with_emission_names_rates_units_and_types(
            names=["ch4"],
            rates=[emission_rate],
            units=[YamlEmissionRateUnits.KILO_PER_DAY],
            rate_types=[RateType.CALENDAR_DAY],
        )
    ).validate()

    installation_sd_kg_per_day = (
        YamlInstallationBuilder()
        .with_name("minimal_installation")
        .with_category(InstallationUserDefinedCategoryType.FIXED)
        .with_fuel_consumers([fuel_consumer_direct(fuel_turbine.name, fuel_rate)])
        .with_venting_emitters([venting_emitter_sd_kg_per_day])
        .with_regularity(regularity)
    ).validate()

    installation_sd_tons_per_day = (
        YamlInstallationBuilder()
        .with_name("minimal_installation")
        .with_category(InstallationUserDefinedCategoryType.FIXED)
        .with_fuel_consumers([fuel_consumer_direct(fuel_turbine.name, fuel_rate)])
        .with_venting_emitters([venting_emitter_sd_tons_per_day])
        .with_regularity(regularity)
    ).validate()

    installation_cd_kg_per_day = (
        YamlInstallationBuilder()
        .with_name("minimal_installation")
        .with_category(InstallationUserDefinedCategoryType.FIXED)
        .with_fuel_consumers([fuel_consumer_direct(fuel_turbine.name, fuel_rate)])
        .with_venting_emitters([venting_emitter_cd_kg_per_day])
        .with_regularity(regularity)
    ).validate()

    asset_sd_kg_per_day = get_asset_yaml_model(
        installations=[installation_sd_kg_per_day], time_vector=time_vector, frequency=Frequency.YEAR
    )

    asset_sd_tons_per_day = get_asset_yaml_model(
        installations=[installation_sd_tons_per_day], time_vector=time_vector, frequency=Frequency.YEAR
    )

    asset_cd_kg_per_day = get_asset_yaml_model(
        installations=[installation_cd_kg_per_day], time_vector=time_vector, frequency=Frequency.YEAR
    )

    ltp_result_input_sd_kg_per_day = get_consumption(
        model=asset_sd_kg_per_day,
        variables_map=variables_map,
        frequency=Frequency.YEAR,
        periods=variables_map.get_periods(),
    )

    ltp_result_input_sd_tons_per_day = get_consumption(
        model=asset_sd_tons_per_day,
        variables_map=variables_map,
        frequency=Frequency.YEAR,
        periods=variables_map.get_periods(),
    )

    ltp_result_input_cd_kg_per_day = get_consumption(
        model=asset_cd_kg_per_day,
        variables_map=variables_map,
        frequency=Frequency.YEAR,
        periods=variables_map.get_periods(),
    )

    emission_input_sd_kg_per_day = get_sum_ltp_column(
        ltp_result_input_sd_kg_per_day, installation_nr=0, ltp_column="storageCh4Mass"
    )
    emission_input_sd_tons_per_day = get_sum_ltp_column(
        ltp_result_input_sd_tons_per_day, installation_nr=0, ltp_column="storageCh4Mass"
    )
    emission_input_cd_kg_per_day = get_sum_ltp_column(
        ltp_result_input_cd_kg_per_day, installation_nr=0, ltp_column="storageCh4Mass"
    )

    # Verify correct emissions when input is kg per day. Output should be in tons per day - hence dividing by 1000
    assert emission_input_sd_kg_per_day == (emission_rate / 1000) * 365 * regularity

    # Verify correct emissions when input is tons per day.
    assert emission_input_sd_tons_per_day == emission_rate * 365 * regularity

    # Verify that input calendar day vs input stream day is linked correctly through regularity
    assert emission_input_cd_kg_per_day == emission_input_sd_kg_per_day / regularity

    # Verify that results is independent of regularity, when input rate is in calendar days
    assert emission_input_cd_kg_per_day == (emission_rate / 1000) * 365


def test_only_venting_emitters_no_fuelconsumers(fuel_consumer_direct, fuel_turbine):
    """
    Test that it is possible with only venting emitters, without fuelconsumers.
    """
    time_vector = [
        datetime(2027, 1, 1),
        datetime(2028, 1, 1),
    ]
    regularity = 0.2
    emission_rate = 10

    variables_map = VariablesMap(time_vector=time_vector, variables={})

    # Installation with only venting emitters:
    venting_emitter = (
        YamlVentingEmitterDirectTypeBuilder()
        .with_name("Venting emitter 1")
        .with_category(ConsumerUserDefinedCategoryType.STORAGE)
        .with_emission_names_rates_units_and_types(
            names=["ch4"],
            rates=[emission_rate],
            units=[YamlEmissionRateUnits.KILO_PER_DAY],
            rate_types=[RateType.STREAM_DAY],
        )
    ).validate()

    installation_only_emitters = (
        YamlInstallationBuilder()
        .with_name("Venting emitter installation")
        .with_category(InstallationUserDefinedCategoryType.FIXED)
        .with_venting_emitters([venting_emitter])
        .with_regularity(regularity)
    ).validate()

    asset = get_asset_yaml_model(
        installations=[installation_only_emitters], time_vector=time_vector, frequency=Frequency.YEAR
    )

    venting_emitter_only_results = get_consumption(
        model=asset, variables_map=variables_map, frequency=Frequency.YEAR, periods=variables_map.get_periods()
    )

    # Verify that eCalc is not failing in get_asset_result with only venting emitters -
    # when installation result is empty, i.e. with no genset and fuel consumers:
    assert isinstance(calculate_asset_result(model=asset, variables=variables_map), EcalcModelResult)

    # Verify correct emissions:
    emissions_ch4 = get_sum_ltp_column(venting_emitter_only_results, installation_nr=0, ltp_column="storageCh4Mass")
    assert emissions_ch4 == (emission_rate / 1000) * 365 * regularity

    # Installation with only fuel consumers:
    installation_only_fuel_consumers = (
        YamlInstallationBuilder()
        .with_name("Fuel consumer installation")
        .with_category(InstallationUserDefinedCategoryType.FIXED)
        .with_fuel_consumers([fuel_consumer_direct(fuel_turbine.name)])
        .with_regularity(regularity)
    ).validate()

    asset_multi_installations = get_asset_yaml_model(
        installations=[installation_only_emitters, installation_only_fuel_consumers],
        fuel_types=[fuel_turbine],
        time_vector=time_vector,
        frequency=Frequency.YEAR,
    )

    # Verify that eCalc is not failing in get_asset_result, with only venting emitters -
    # when installation result is empty for one installation, i.e. with no genset and fuel consumers.
    # Include asset with two installations, one with only emitters and one with only fuel consumers -
    # ensure that get_asset_result returns a result:
    assert isinstance(
        calculate_asset_result(model=asset_multi_installations, variables=variables_map), EcalcModelResult
    )

    asset_ltp_result = get_consumption(
        model=asset_multi_installations,
        variables_map=variables_map,
        frequency=Frequency.YEAR,
        periods=variables_map.get_periods(),
    )

    # Check that the results are the same: For the case with only one installation (only venting emitters),
    # compared to the multi-installation case with two installations. The fuel-consumer installation should
    # give no CH4-contribution (only CO2)
    emissions_ch4_asset = get_sum_ltp_column(asset_ltp_result, installation_nr=0, ltp_column="storageCh4Mass")
    assert emissions_ch4 == emissions_ch4_asset


def test_power_from_shore(
    el_consumer_direct_base_load,
    fuel_multi,
    resource_service_factory,
    generator_electricity2fuel_17MW_resource,
    onshore_power_electricity2fuel_resource,
    cable_loss_time_series_resource,
):
    """Test power from shore output for LTP export."""

    time_vector_yearly = pd.date_range(datetime(2025, 1, 1), datetime(2031, 1, 1), freq="YS").to_pydatetime().tolist()

    variables_map = VariablesMap(time_vector=time_vector_yearly, variables={})
    regularity = 0.2
    load = 10
    cable_loss = 0.1
    max_from_shore = 12

    generator_energy_function = (
        YamlElectricity2fuelBuilder().with_name("generator_energy_function").with_file("generator_energy_function")
    ).validate()

    power_from_shore_energy_function = (
        YamlElectricity2fuelBuilder().with_name("pfs_energy_function").with_file("pfs_energy_function")
    ).validate()

    cable_loss_time_series = (
        YamlTimeSeriesBuilder().with_name("CABLE_LOSS").with_type("DEFAULT").with_file("CABLE_LOSS")
    ).validate()

    generator_set = (
        YamlGeneratorSetBuilder()
        .with_name("generator1")
        .with_category(
            {
                datetime(2025, 1, 1): ConsumerUserDefinedCategoryType.TURBINE_GENERATOR,
                datetime(2027, 1, 1): ConsumerUserDefinedCategoryType.POWER_FROM_SHORE,
            }
        )
        .with_electricity2fuel(
            {
                datetime(2025, 1, 1): generator_energy_function.name,
                datetime(2027, 1, 1): power_from_shore_energy_function.name,
            }
        )
        .with_consumers([el_consumer_direct_base_load(el_reference_name="base_load", load=load)])
        .with_cable_loss(cable_loss)
        .with_max_usage_from_shore(max_from_shore)
    ).validate()

    installation_pfs = (
        YamlInstallationBuilder()
        .with_name("minimal_installation")
        .with_category(InstallationUserDefinedCategoryType.FIXED)
        .with_fuel(fuel_multi.name)
        .with_generator_sets([generator_set])
        .with_regularity(regularity)
    ).validate()

    resources = {
        generator_energy_function.name: generator_electricity2fuel_17MW_resource,
        power_from_shore_energy_function.name: onshore_power_electricity2fuel_resource,
        cable_loss_time_series.name: cable_loss_time_series_resource,
    }
    resource_service = resource_service_factory(resources=resources)

    asset_pfs = get_asset_yaml_model(
        installations=[installation_pfs],
        fuel_types=[fuel_multi],
        time_vector=time_vector_yearly,
        time_series=[cable_loss_time_series],
        facility_inputs=[generator_energy_function, power_from_shore_energy_function],
        frequency=Frequency.YEAR,
        resource_service=resource_service,
    )

    generator_set_csv = deepcopy(generator_set)
    generator_set_csv.cable_loss = "CABLE_LOSS;CABLE_LOSS_FACTOR"

    installation_pfs_csv = (
        YamlInstallationBuilder()
        .with_name("minimal_installation_csv")
        .with_category(InstallationUserDefinedCategoryType.FIXED)
        .with_fuel(fuel_multi.name)
        .with_generator_sets([generator_set_csv])
        .with_regularity(regularity)
    ).validate()

    asset_pfs_csv = get_asset_yaml_model(
        installations=[installation_pfs_csv],
        fuel_types=[fuel_multi],
        time_vector=time_vector_yearly,
        time_series=[cable_loss_time_series],
        facility_inputs=[generator_energy_function, power_from_shore_energy_function],
        frequency=Frequency.YEAR,
        resource_service=resource_service,
    )

    ltp_result = get_consumption(
        model=asset_pfs,
        variables_map=asset_pfs.variables,
        periods=asset_pfs.variables.get_periods(),
        frequency=Frequency.YEAR,
    )

    ltp_result_csv = get_consumption(
        model=asset_pfs_csv,
        variables_map=asset_pfs_csv.variables,
        periods=asset_pfs_csv.variables.get_periods(),
        frequency=Frequency.YEAR,
    )

    power_from_shore_consumption = get_sum_ltp_column(
        ltp_result=ltp_result, installation_nr=0, ltp_column="fromShoreConsumption"
    )
    power_supply_onshore = get_sum_ltp_column(ltp_result=ltp_result, installation_nr=0, ltp_column="powerSupplyOnshore")
    max_usage_from_shore = get_sum_ltp_column(
        ltp_result=ltp_result, installation_nr=0, ltp_column="fromShorePeakMaximum"
    )

    power_supply_onshore_csv = get_sum_ltp_column(
        ltp_result=ltp_result_csv, installation_nr=0, ltp_column="powerSupplyOnshore"
    )

    # In the temporal model, the category is POWER_FROM_SHORE the last three years, within the period 2025 - 2030:
    delta_days = calculate_delta_days(time_vector_yearly)[2:6]

    # Check that power from shore consumption is correct
    assert power_from_shore_consumption == sum([load * days * regularity * 24 / 1000 for days in delta_days])

    # Check that power supply onshore is power from shore consumption * (1 + cable loss)
    assert power_supply_onshore == pytest.approx(
        sum([load * (1 + cable_loss) * days * regularity * 24 / 1000 for days in delta_days])
    )

    # Check that max usage from shore is just a report of the input
    # Max usage from shore is 0 until 2027.6.1 and the 12 until 2031.1.1, so
    # 2027, 2028, 2029 and 2030 (4 years) should all have 12 as max usage from shore.
    assert max_usage_from_shore == max_from_shore * 4

    # Check that reading cable loss from csv-file gives same result as using constant
    assert power_supply_onshore == power_supply_onshore_csv

    # Verify correct unit for max usage from shore
    assert (
        get_ltp_column(ltp_result=ltp_result, installation_nr=0, ltp_column="fromShorePeakMaximum").unit
        == Unit.MEGA_WATT
    )
