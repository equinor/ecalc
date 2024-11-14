import pytest
from datetime import datetime
from io import StringIO
from typing import cast, Optional, Union
from pathlib import Path
import numpy as np

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
from libecalc.common.time_utils import Period
from libecalc.testing.yaml_builder import (
    YamlFuelTypeBuilder,
    YamlFuelConsumerBuilder,
    YamlInstallationBuilder,
    YamlEnergyUsageModelDirectBuilder,
    YamlAssetBuilder,
    YamlVentingEmitterDirectTypeBuilder,
)
from ecalc_cli.infrastructure.file_resource_service import FileResourceService
from libecalc.dto.types import (
    FuelTypeUserDefinedCategoryType,
    ConsumerUserDefinedCategoryType,
    InstallationUserDefinedCategoryType,
)
from libecalc.presentation.yaml.yaml_types.components.yaml_asset import YamlAsset
from libecalc.presentation.yaml.yaml_types.components.yaml_installation import YamlInstallation
from libecalc.presentation.yaml.yaml_types.components.legacy.energy_usage_model.yaml_energy_usage_model_direct import (
    ConsumptionRateType,
)
from libecalc.presentation.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel
from libecalc.presentation.yaml.yaml_entities import ResourceStream
from libecalc.presentation.yaml.configuration_service import ConfigurationService
from libecalc.presentation.yaml.yaml_models.yaml_model import ReaderType, YamlConfiguration, YamlValidator
from libecalc.common.time_utils import Frequency, Periods
from libecalc.presentation.yaml.model import YamlModel
from libecalc.expression import Expression
from libecalc.presentation.yaml.yaml_types.yaml_stream_conditions import (
    YamlEmissionRateUnits,
)
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


def get_yaml_model(yaml_string: str, frequency: Frequency):
    configuration_service = OverridableStreamConfigurationService(
        stream=ResourceStream(name="", stream=StringIO(yaml_string)),
    )
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
):
    asset = (
        YamlAssetBuilder()
        .with_installations(installations=installations)
        .with_start(time_vector[0])
        .with_end(time_vector[1])
    )

    if fuel_types is not None:
        asset.fuel_types = fuel_types

    asset = asset.validate()

    asset_dict = asset.model_dump(
        serialize_as_any=True,
        mode="json",
        exclude_unset=True,
        by_alias=True,
    )

    asset_yaml_string = PyYamlYamlModel.dump_yaml(yaml_dict=asset_dict)
    asset_yaml_model = get_yaml_model(yaml_string=asset_yaml_string, frequency=frequency)

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
def energy_usage_model_direct():
    return (
        YamlEnergyUsageModelDirectBuilder()
        .with_fuel_rate(fuel_rate)
        .with_consumption_rate_type(ConsumptionRateType.STREAM_DAY)
    ).validate()


@pytest.fixture
def fuel_consumer_direct(fuel_turbine, energy_usage_model_direct):
    def fuel_consumer(fuel_reference_name: str):
        return (
            YamlFuelConsumerBuilder()
            .with_name("fuel_consumer")
            .with_fuel(fuel_reference_name)
            .with_category(ConsumerUserDefinedCategoryType.FLARE)
            .with_energy_usage_model(energy_usage_model_direct)
        ).validate()

    return fuel_consumer


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


def test_fuel_emissions(fuel_turbine, installation_boiler_heater):
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
        .with_fuel_consumers([fuel_consumer_direct(fuel_turbine.name)])
        .with_venting_emitters([venting_emitter_sd_kg_per_day])
        .with_regularity(regularity)
    ).validate()

    installation_sd_tons_per_day = (
        YamlInstallationBuilder()
        .with_name("minimal_installation")
        .with_category(InstallationUserDefinedCategoryType.FIXED)
        .with_fuel_consumers([fuel_consumer_direct(fuel_turbine.name)])
        .with_venting_emitters([venting_emitter_sd_tons_per_day])
        .with_regularity(regularity)
    ).validate()

    installation_cd_kg_per_day = (
        YamlInstallationBuilder()
        .with_name("minimal_installation")
        .with_category(InstallationUserDefinedCategoryType.FIXED)
        .with_fuel_consumers([fuel_consumer_direct(fuel_turbine.name)])
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
