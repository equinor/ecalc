from copy import deepcopy
from datetime import datetime

import pandas as pd
import pytest

from libecalc.common.time_utils import Frequency, calculate_delta_days, Period
from libecalc.common.units import Unit
from libecalc.common.utils.rates import RateType
from libecalc.common.variables import VariablesMap
from libecalc.dto.types import ConsumerUserDefinedCategoryType, InstallationUserDefinedCategoryType
from libecalc.presentation.json_result.result import EcalcModelResult
from libecalc.presentation.yaml.yaml_entities import MemoryResource
from libecalc.presentation.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel
from libecalc.presentation.yaml.yaml_types.yaml_stream_conditions import YamlEmissionRateUnits
from libecalc.testing.yaml_builder import (
    YamlAssetBuilder,
    YamlVentingEmitterDirectTypeBuilder,
    YamlInstallationBuilder,
    YamlElectricity2fuelBuilder,
    YamlTimeSeriesBuilder,
    YamlGeneratorSetBuilder,
    YamlEnergyUsageModelCompressorBuilder,
    YamlCompressorTabularBuilder,
    YamlFuelConsumerBuilder,
)
from tests.libecalc.presentation.exporter.conftest import (
    get_consumption,
    get_sum_ltp_column,
    expected_boiler_fuel_consumption,
    expected_heater_fuel_consumption,
    expected_co2_from_boiler,
    expected_co2_from_heater,
    get_asset_yaml_model,
    calculate_asset_result,
    get_ltp_column,
    expected_co2_from_diesel,
    expected_nox_from_diesel,
    expected_nmvoc_from_diesel,
    expected_ch4_from_diesel,
    expected_fuel_consumption,
    expected_diesel_consumption,
    expected_co2_from_fuel,
    expected_pfs_el_consumption,
    expected_gas_turbine_el_generated,
    expected_offshore_wind_el_consumption,
    category_dict_coarse,
    category_dict,
    expected_gas_turbine_compressor_el_consumption,
)

from tests.libecalc.presentation.exporter.memory_resources import (
    generator_electricity2fuel_17MW_resource,
    onshore_power_electricity2fuel_resource,
    cable_loss_time_series_resource,
    compressor_sampled_fuel_driven_resource,
    generator_fuel_power_to_fuel_resource,
    generator_diesel_power_to_fuel_resource,
)

date1 = datetime(2027, 1, 1)
date2 = datetime(2027, 4, 10)
date3 = datetime(2028, 1, 1)
date4 = datetime(2028, 4, 10)
date5 = datetime(2029, 1, 1)

period1 = Period(date1, date2)
period2 = Period(date2, date3)
period3 = Period(date3, date4)
period4 = Period(date4, date5)
period5 = Period(date5)

time_vector_installation = [date1, date2, date3, date4, date5]

period_from_date1 = Period(date1)
period_from_date3 = Period(date3)

power_usage_mw = 10
power_offshore_wind_mw = 1
power_compressor_mw = 3

fuel_rate = 67000
diesel_rate = 120000

load_consumer = 10
compressor_rate = 3000000
regularity_installation = 1.0

co2_factor = 1
ch4_factor = 0.1
nox_factor = 0.5
nmvoc_factor = 0

# Calculate expected values for consumption and emissions
calculated_co2_from_diesel = expected_co2_from_diesel(diesel_rate, regularity_installation, co2_factor)
calculated_co2_from_fuel = expected_co2_from_fuel(fuel_rate, regularity_installation, co2_factor)
calculated_co2_from_boiler = expected_co2_from_boiler(fuel_rate, regularity_installation, co2_factor)
calculated_co2_from_heater = expected_co2_from_heater(fuel_rate, regularity_installation, co2_factor)

calculated_nox_from_diesel = expected_nox_from_diesel(diesel_rate, regularity_installation, nox_factor)
calculated_nmvoc_from_diesel = expected_nmvoc_from_diesel(diesel_rate, regularity_installation, nmvoc_factor)
calculated_ch4_from_diesel = expected_ch4_from_diesel(diesel_rate, regularity_installation, ch4_factor)

calculated_fuel_consumption = expected_fuel_consumption(fuel_rate, regularity_installation)
calculated_boiler_fuel_consumption = expected_boiler_fuel_consumption(fuel_rate, regularity_installation)
calculated_heater_fuel_consumption = expected_heater_fuel_consumption(fuel_rate, regularity_installation)

calculated_diesel_consumption = expected_diesel_consumption(diesel_rate, regularity_installation)

calculated_gas_turbine_el_generated = expected_gas_turbine_el_generated(power_usage_mw, regularity_installation)
calculated_pfs_el_consumption = expected_pfs_el_consumption(power_usage_mw, regularity_installation)
calculated_gas_turbine_compressor_el_consumption = expected_gas_turbine_compressor_el_consumption(power_compressor_mw)
calculated_offshore_wind_el_consumption = expected_offshore_wind_el_consumption(
    power_offshore_wind_mw, regularity_installation
)


def create_variables_map(time_vector, rate_values=None):
    variables = {"RATE": rate_values} if rate_values else {}
    return VariablesMap(time_vector=time_vector, variables=variables)


def get_ltp_result(model, variables, frequency=Frequency.YEAR):
    return get_consumption(model=model, variables=variables, periods=variables.get_periods(), frequency=frequency)


def test_emissions_diesel_fixed_and_mobile(
    generator_diesel_power_to_fuel_resource,
    generator_fuel_power_to_fuel_resource,
    temporal_dict,
    el_consumer_direct_base_load,
    resource_service_factory,
    fuel_multi_temporal,
    fuel_gas,
    diesel,
):
    """Test reporting of CH4 from diesel in LTP."""

    fuel = fuel_gas(["co2"], [co2_factor])
    fuel_diesel = diesel(["co2", "ch4", "nox", "nmvoc"], [co2_factor, ch4_factor, nox_factor, nmvoc_factor])

    generator_diesel_energy_function = (
        YamlElectricity2fuelBuilder()
        .with_name("generator_diesel_energy_function")
        .with_file("generator_diesel_energy_function")
    ).validate()

    generator_fuel_energy_function = (
        YamlElectricity2fuelBuilder()
        .with_name("generator_fuel_energy_function")
        .with_file("generator_fuel_energy_function")
    ).validate()

    generator_fixed = (
        YamlGeneratorSetBuilder()
        .with_name("generator_fixed")
        .with_category(category_dict())
        .with_consumers([el_consumer_direct_base_load(el_reference_name="base_load", load=load_consumer)])
        .with_electricity2fuel(
            temporal_dict(
                reference1=generator_diesel_energy_function.name,
                reference2=generator_fuel_energy_function.name,
            )
        )
    ).validate()

    generator_mobile = deepcopy(generator_fixed)
    generator_mobile.name = "generator_mobile"

    installation_fixed = (
        YamlInstallationBuilder()
        .with_name("INSTALLATION_FIXED")
        .with_regularity(regularity_installation)
        .with_fuel(fuel_multi_temporal(fuel_diesel, fuel))
        .with_category(InstallationUserDefinedCategoryType.FIXED)
        .with_generator_sets([generator_fixed])
    ).validate()

    installation_mobile = (
        YamlInstallationBuilder()
        .with_name("INSTALLATION_MOBILE")
        .with_regularity(regularity_installation)
        .with_fuel(fuel_multi_temporal(fuel_diesel, fuel))
        .with_category(InstallationUserDefinedCategoryType.MOBILE)
        .with_generator_sets([generator_mobile])
    ).validate()

    resources = {
        generator_diesel_energy_function.name: generator_diesel_power_to_fuel_resource(
            power_usage_mw=power_usage_mw, diesel_rate=diesel_rate
        ),
        generator_fuel_energy_function.name: generator_fuel_power_to_fuel_resource(
            power_usage_mw=power_usage_mw, fuel_rate=fuel_rate
        ),
    }
    resource_service = resource_service_factory(resources=resources)

    asset = get_asset_yaml_model(
        installations=[installation_fixed, installation_mobile],
        fuel_types=[fuel, fuel_diesel],
        time_vector=time_vector_installation,
        facility_inputs=[generator_diesel_energy_function, generator_fuel_energy_function],
        frequency=Frequency.YEAR,
        resource_service=resource_service,
    )

    variables = create_variables_map(time_vector_installation, rate_values=[1, 1, 1, 1])
    ltp_result = get_ltp_result(asset, variables)

    co2_from_diesel_fixed = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column="engineDieselCo2Mass")
    co2_from_diesel_mobile = get_sum_ltp_column(ltp_result, installation_nr=1, ltp_column="engineNoCo2TaxDieselCo2Mass")

    nox_from_diesel_fixed = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column="engineDieselNoxMass")
    nox_from_diesel_mobile = get_sum_ltp_column(ltp_result, installation_nr=1, ltp_column="engineNoCo2TaxDieselNoxMass")

    nmvoc_from_diesel_fixed = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column="engineDieselNmvocMass")
    nmvoc_from_diesel_mobile = get_sum_ltp_column(
        ltp_result, installation_nr=1, ltp_column="engineNoCo2TaxDieselNmvocMass"
    )

    ch4_from_diesel_fixed = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column="engineDieselCh4Mass")
    ch4_from_diesel_mobile = get_sum_ltp_column(ltp_result, installation_nr=1, ltp_column="engineNoCo2TaxDieselCh4Mass")

    assert co2_from_diesel_fixed == calculated_co2_from_diesel
    assert co2_from_diesel_mobile == calculated_co2_from_diesel
    assert nox_from_diesel_fixed == calculated_nox_from_diesel
    assert nox_from_diesel_mobile == calculated_nox_from_diesel
    assert nmvoc_from_diesel_fixed == calculated_nmvoc_from_diesel
    assert nmvoc_from_diesel_mobile == calculated_nmvoc_from_diesel
    assert ch4_from_diesel_fixed == calculated_ch4_from_diesel
    assert ch4_from_diesel_mobile == calculated_ch4_from_diesel


def test_temporal_models_detailed(
    temporal_dict,
    fuel_multi_temporal,
    diesel,
    fuel_gas,
    generator_diesel_power_to_fuel_resource,
    generator_fuel_power_to_fuel_resource,
    resource_service_factory,
    el_consumer_direct_base_load,
):
    """Test various queries for LTP reporting. Purpose: ensure that variations in temporal models are captured.

    Detailed temporal models (variations within one year) for:
    - Fuel type
    - Generator set user defined category
    - Generator set model
    """
    variables = create_variables_map(time_vector_installation, rate_values=[1, 1, 1, 1])
    fuel = fuel_gas(["co2"], [co2_factor])
    diesel = diesel(["co2"], [co2_factor])

    generator_diesel_energy_function = (
        YamlElectricity2fuelBuilder()
        .with_name("generator_diesel_energy_function")
        .with_file("generator_diesel_energy_function")
    ).validate()

    generator_fuel_energy_function = (
        YamlElectricity2fuelBuilder()
        .with_name("generator_fuel_energy_function")
        .with_file("generator_fuel_energy_function")
    ).validate()

    generator_set = (
        YamlGeneratorSetBuilder()
        .with_name("generator_set")
        .with_category(category_dict_coarse())
        .with_consumers([el_consumer_direct_base_load(el_reference_name="base_load", load=load_consumer)])
        .with_electricity2fuel(
            temporal_dict(
                reference1=generator_diesel_energy_function.name,
                reference2=generator_fuel_energy_function.name,
            )
        )
    ).validate()

    installation = (
        YamlInstallationBuilder()
        .with_name("INSTALLATION A")
        .with_generator_sets([generator_set])
        .with_fuel(fuel_multi_temporal(fuel1=diesel, fuel2=fuel))
        .with_category(InstallationUserDefinedCategoryType.FIXED)
    ).validate()

    resources = {
        generator_diesel_energy_function.name: generator_diesel_power_to_fuel_resource(
            power_usage_mw=power_usage_mw,
            diesel_rate=diesel_rate,
        ),
        generator_fuel_energy_function.name: generator_fuel_power_to_fuel_resource(
            power_usage_mw=power_usage_mw,
            fuel_rate=fuel_rate,
        ),
    }
    resource_service = resource_service_factory(resources=resources)

    asset = get_asset_yaml_model(
        installations=[installation],
        fuel_types=[fuel, diesel],
        time_vector=time_vector_installation,
        facility_inputs=[generator_diesel_energy_function, generator_fuel_energy_function],
        frequency=Frequency.YEAR,
        resource_service=resource_service,
    )

    ltp_result = get_ltp_result(asset, variables)

    turbine_fuel_consumption = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column="turbineFuelGasConsumption")
    engine_diesel_consumption = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column="engineDieselConsumption")

    gas_turbine_el_generated = get_sum_ltp_column(
        ltp_result, installation_nr=0, ltp_column="gasTurbineGeneratorConsumption"
    )
    pfs_el_consumption = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column="fromShoreConsumption")

    co2_from_fuel = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column="turbineFuelGasCo2Mass")
    co2_from_diesel = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column="engineDieselCo2Mass")

    # FuelQuery: Check that turbine fuel consumption is included,
    # even if the temporal model starts with diesel every year
    assert turbine_fuel_consumption != 0

    # FuelQuery: Check that turbine fuel consumption is correct
    assert turbine_fuel_consumption == calculated_fuel_consumption

    # FuelQuery: Check that turbine fuel gas is not categorized as diesel,
    # even if the temporal model starts with diesel every year
    assert engine_diesel_consumption != calculated_diesel_consumption + calculated_fuel_consumption

    # FuelQuery: Check that diesel consumption is correct
    assert engine_diesel_consumption == pytest.approx(calculated_diesel_consumption, 0.00001)

    # ElectricityGeneratedQuery: Check that turbine power generation is correct.
    assert gas_turbine_el_generated == pytest.approx(calculated_gas_turbine_el_generated, 0.00001)

    # ElectricityGeneratedQuery: Check that power from shore el consumption is correct.
    assert pfs_el_consumption == pytest.approx(calculated_pfs_el_consumption, 0.00001)

    # EmissionQuery. Check that co2 from fuel is correct.
    assert co2_from_fuel == calculated_co2_from_fuel

    # EmissionQuery: Emissions. Check that co2 from diesel is correct.
    assert co2_from_diesel == calculated_co2_from_diesel


def test_temporal_models_offshore_wind(
    el_consumer_direct_base_load,
    offshore_wind_consumer,
    fuel_gas,
    generator_fuel_power_to_fuel_resource,
    resource_service_factory,
):
    """Test ElConsumerPowerConsumptionQuery for calculating offshore wind el-consumption, LTP.

    Detailed temporal models (variations within one year) for:
    - El-consumer user defined category
    - El-consumer energy usage model
    """
    variables = create_variables_map(time_vector_installation, rate_values=[1, 1, 1, 1])
    fuel = fuel_gas(["co2"], [co2_factor])

    generator_fuel_energy_function = (
        YamlElectricity2fuelBuilder()
        .with_name("generator_fuel_energy_function")
        .with_file("generator_fuel_energy_function")
    ).validate()

    generator_set = (
        YamlGeneratorSetBuilder()
        .with_name("generator_set")
        .with_category({period_from_date1.start: ConsumerUserDefinedCategoryType.TURBINE_GENERATOR})
        .with_consumers([offshore_wind_consumer(power_offshore_wind_mw)])
        .with_electricity2fuel({period_from_date1.start: generator_fuel_energy_function.name})
    ).validate()

    installation = (
        YamlInstallationBuilder()
        .with_name("INSTALLATION A")
        .with_generator_sets([generator_set])
        .with_fuel(fuel.name)
        .with_category(InstallationUserDefinedCategoryType.FIXED)
    ).validate()

    resources = {
        generator_fuel_energy_function.name: generator_fuel_power_to_fuel_resource(
            power_usage_mw=power_usage_mw,
            fuel_rate=fuel_rate,
        ),
    }

    resource_service = resource_service_factory(resources=resources)

    asset = get_asset_yaml_model(
        installations=[installation],
        fuel_types=[fuel],
        time_vector=time_vector_installation,
        facility_inputs=[generator_fuel_energy_function],
        frequency=Frequency.YEAR,
        resource_service=resource_service,
    )

    ltp_result = get_ltp_result(asset, variables)

    offshore_wind_el_consumption = get_sum_ltp_column(
        ltp_result, installation_nr=0, ltp_column="offshoreWindConsumption"
    )

    # ElConsumerPowerConsumptionQuery: Check that offshore wind el-consumption is correct.
    assert offshore_wind_el_consumption == calculated_offshore_wind_el_consumption


def test_temporal_models_compressor(
    generator_fuel_power_to_fuel_resource,
    compressor_sampled_fuel_driven_resource,
    resource_service_factory,
    fuel_gas,
    temporal_dict,
):
    """Test FuelConsumerPowerConsumptionQuery for calculating gas turbine compressor el-consumption, LTP.

    Detailed temporal models (variations within one year) for:
    - Fuel consumer user defined category
    """
    variables = create_variables_map(time_vector_installation, rate_values=[1, 1, 1, 1])
    fuel = fuel_gas(["co2"], [co2_factor])

    generator_fuel_energy_function = (
        YamlElectricity2fuelBuilder()
        .with_name("generator_fuel_energy_function")
        .with_file("generator_fuel_energy_function")
    ).validate()

    compressor_energy_function = (
        YamlCompressorTabularBuilder().with_name("compressor_energy_function").with_file("compressor_energy_function")
    ).validate()

    compressor_energy_usage_model = (
        YamlEnergyUsageModelCompressorBuilder()
        .with_rate(compressor_rate)
        .with_suction_pressure(200)
        .with_discharge_pressure(400)
        .with_energy_function(compressor_energy_function.name)
    ).validate()

    fuel_consumer = (
        YamlFuelConsumerBuilder()
        .with_name("fuel_consumer")
        .with_fuel({period_from_date1.start: fuel.name})
        .with_energy_usage_model(compressor_energy_usage_model)
        .with_category(
            temporal_dict(
                reference1=ConsumerUserDefinedCategoryType.MISCELLANEOUS,
                reference2=ConsumerUserDefinedCategoryType.GAS_DRIVEN_COMPRESSOR,
            )
        )
    ).validate()

    generator_set = (
        YamlGeneratorSetBuilder()
        .with_name("generator_set")
        .with_category({period_from_date1.start: ConsumerUserDefinedCategoryType.TURBINE_GENERATOR})
        .with_electricity2fuel({period_from_date1.start: generator_fuel_energy_function.name})
    ).validate()

    installation = (
        YamlInstallationBuilder()
        .with_name("INSTALLATION A")
        .with_generator_sets([generator_set])
        .with_fuel(fuel.name)
        .with_fuel_consumers([fuel_consumer])
        .with_category(InstallationUserDefinedCategoryType.FIXED)
    ).validate()

    resources = {
        generator_fuel_energy_function.name: generator_fuel_power_to_fuel_resource(
            power_usage_mw=power_usage_mw,
            fuel_rate=fuel_rate,
        ),
        compressor_energy_function.name: compressor_sampled_fuel_driven_resource(
            compressor_rate=compressor_rate, power_compressor_mw=power_compressor_mw
        ),
    }

    resource_service = resource_service_factory(resources=resources)

    asset = get_asset_yaml_model(
        installations=[installation],
        fuel_types=[fuel],
        time_vector=time_vector_installation,
        facility_inputs=[generator_fuel_energy_function, compressor_energy_function],
        frequency=Frequency.YEAR,
        resource_service=resource_service,
    )

    ltp_result = get_ltp_result(asset, variables)

    gas_turbine_compressor_el_consumption = get_sum_ltp_column(
        ltp_result, installation_nr=0, ltp_column="gasTurbineCompressorConsumption"
    )

    # FuelConsumerPowerConsumptionQuery. Check gas turbine compressor el consumption.
    assert gas_turbine_compressor_el_consumption == calculated_gas_turbine_compressor_el_consumption


def test_boiler_heater_categories(fuel_gas, installation_boiler_heater):
    variables = create_variables_map(time_vector_installation)
    fuel = fuel_gas(["co2"], [co2_factor])

    asset = get_asset_yaml_model(
        installations=[installation_boiler_heater],
        fuel_types=[fuel],
        time_vector=[date1, date5],
        frequency=Frequency.YEAR,
    )

    ltp_result = get_ltp_result(asset, variables)

    boiler_fuel_consumption = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column="boilerFuelGasConsumption")
    heater_fuel_consumption = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column="heaterFuelGasConsumption")
    co2_from_boiler = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column="boilerFuelGasCo2Mass")
    co2_from_heater = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column="heaterFuelGasCo2Mass")

    assert boiler_fuel_consumption == calculated_boiler_fuel_consumption
    assert heater_fuel_consumption == calculated_heater_fuel_consumption
    assert co2_from_boiler == calculated_co2_from_boiler
    assert co2_from_heater == calculated_co2_from_heater


def test_total_oil_loaded_old_method(fuel_gas, fuel_consumer_direct):
    """Test total oil loaded/stored for LTP export. Using original method where direct/venting emitters are
    modelled as FUELSCONSUMERS using DIRECT.

    Verify correct volume when model includes emissions related to both storage and loading of oil,
    and when model includes only loading.
    """
    time_vector = [datetime(2027, 1, 1), datetime(2028, 1, 1)]
    variables = create_variables_map(time_vector)

    regularity = 0.6
    emission_factor = 2
    rate = 100

    fuel = fuel_gas(["ch4"], [emission_factor])
    loading = fuel_consumer_direct(
        fuel_reference_name=fuel.name, rate=rate, name="loading", category=ConsumerUserDefinedCategoryType.LOADING
    )

    storage = fuel_consumer_direct(
        fuel_reference_name=fuel.name, rate=rate, name="storage", category=ConsumerUserDefinedCategoryType.STORAGE
    )

    installation = (
        YamlInstallationBuilder()
        .with_name("minimal_installation")
        .with_fuel(fuel.name)
        .with_fuel_consumers([loading, storage])
        .with_regularity(regularity)
        .with_category(InstallationUserDefinedCategoryType.FIXED)
    ).validate()

    asset = get_asset_yaml_model(
        installations=[installation],
        fuel_types=[fuel],
        time_vector=time_vector_installation,
        frequency=Frequency.YEAR,
    )

    installation_loading_only = (
        YamlInstallationBuilder()
        .with_name("minimal_installation")
        .with_fuel(fuel.name)
        .with_fuel_consumers([loading])
        .with_regularity(regularity)
        .with_category(InstallationUserDefinedCategoryType.FIXED)
    ).validate()

    asset_loading_only = get_asset_yaml_model(
        installations=[installation_loading_only],
        fuel_types=[fuel],
        time_vector=time_vector_installation,
        frequency=Frequency.YEAR,
    )

    ltp_result_loading_storage = get_ltp_result(asset, variables)
    ltp_result_loading_only = get_ltp_result(asset_loading_only, variables)

    loaded_and_stored_oil_loading_and_storage = get_sum_ltp_column(
        ltp_result_loading_storage, installation_nr=0, ltp_column="loadedAndStoredOil"
    )
    loaded_and_stored_oil_loading_only = get_sum_ltp_column(
        ltp_result_loading_only, installation_nr=0, ltp_column="loadedAndStoredOil"
    )

    # Verify output for total oil loaded/stored, if only loading is specified.
    assert loaded_and_stored_oil_loading_only is not None

    # Verify correct volume for oil loaded/stored
    assert loaded_and_stored_oil_loading_and_storage == rate * 365 * regularity

    # Verify that total oil loaded/stored is the same if only loading is specified,
    # compared to a model with both loading and storage.
    assert loaded_and_stored_oil_loading_and_storage == loaded_and_stored_oil_loading_only


def test_venting_emitters(fuel_consumer_direct, fuel_gas):
    """Test venting emitters for LTP export.

    Verify correct behaviour if input rate is given in different units and rate types (sd and cd).
    """

    time_vector = [datetime(2027, 1, 1), datetime(2028, 1, 1)]
    regularity = 0.2
    emission_rate = 10

    variables = create_variables_map(time_vector)
    fuel = fuel_gas(["co2"], [co2_factor])

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
        .with_fuel_consumers([fuel_consumer_direct(fuel.name, fuel_rate)])
        .with_venting_emitters([venting_emitter_sd_kg_per_day])
        .with_regularity(regularity)
    ).validate()

    installation_sd_tons_per_day = (
        YamlInstallationBuilder()
        .with_name("minimal_installation")
        .with_category(InstallationUserDefinedCategoryType.FIXED)
        .with_fuel_consumers([fuel_consumer_direct(fuel.name, fuel_rate)])
        .with_venting_emitters([venting_emitter_sd_tons_per_day])
        .with_regularity(regularity)
    ).validate()

    installation_cd_kg_per_day = (
        YamlInstallationBuilder()
        .with_name("minimal_installation")
        .with_category(InstallationUserDefinedCategoryType.FIXED)
        .with_fuel_consumers([fuel_consumer_direct(fuel.name, fuel_rate)])
        .with_venting_emitters([venting_emitter_cd_kg_per_day])
        .with_regularity(regularity)
    ).validate()

    asset_sd_kg_per_day = get_asset_yaml_model(
        installations=[installation_sd_kg_per_day],
        fuel_types=[fuel],
        time_vector=time_vector,
        frequency=Frequency.YEAR,
    )

    asset_sd_tons_per_day = get_asset_yaml_model(
        installations=[installation_sd_tons_per_day],
        fuel_types=[fuel],
        time_vector=time_vector,
        frequency=Frequency.YEAR,
    )

    asset_cd_kg_per_day = get_asset_yaml_model(
        installations=[installation_cd_kg_per_day],
        fuel_types=[fuel],
        time_vector=time_vector,
        frequency=Frequency.YEAR,
    )

    ltp_result_input_sd_kg_per_day = get_ltp_result(asset_sd_kg_per_day, variables)
    ltp_result_input_sd_tons_per_day = get_ltp_result(asset_sd_tons_per_day, variables)
    ltp_result_input_cd_kg_per_day = get_ltp_result(asset_cd_kg_per_day, variables)

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


def test_only_venting_emitters_no_fuelconsumers(fuel_consumer_direct, fuel_gas):
    """
    Test that it is possible with only venting emitters, without fuelconsumers.
    """
    time_vector = [datetime(2027, 1, 1), datetime(2028, 1, 1)]
    regularity = 0.2
    emission_rate = 10

    variables = create_variables_map(time_vector)
    fuel = fuel_gas(["co2"], [co2_factor])

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

    venting_emitter_only_results = get_ltp_result(asset, variables)

    # Verify that eCalc is not failing in get_asset_result with only venting emitters -
    # when installation result is empty, i.e. with no genset and fuel consumers:
    assert isinstance(calculate_asset_result(model=asset, variables=variables), EcalcModelResult)

    # Verify correct emissions:
    emissions_ch4 = get_sum_ltp_column(venting_emitter_only_results, installation_nr=0, ltp_column="storageCh4Mass")
    assert emissions_ch4 == (emission_rate / 1000) * 365 * regularity

    # Installation with only fuel consumers:
    installation_only_fuel_consumers = (
        YamlInstallationBuilder()
        .with_name("Fuel consumer installation")
        .with_category(InstallationUserDefinedCategoryType.FIXED)
        .with_fuel_consumers([fuel_consumer_direct(fuel_reference_name=fuel.name, rate=fuel_rate)])
        .with_regularity(regularity)
    ).validate()

    asset_multi_installations = get_asset_yaml_model(
        installations=[installation_only_emitters, installation_only_fuel_consumers],
        fuel_types=[fuel],
        time_vector=time_vector,
        frequency=Frequency.YEAR,
    )

    # Verify that eCalc is not failing in get_asset_result, with only venting emitters -
    # when installation result is empty for one installation, i.e. with no genset and fuel consumers.
    # Include asset with two installations, one with only emitters and one with only fuel consumers -
    # ensure that get_asset_result returns a result:
    assert isinstance(calculate_asset_result(model=asset_multi_installations, variables=variables), EcalcModelResult)

    asset_ltp_result = get_ltp_result(asset_multi_installations, variables)

    # Check that the results are the same: For the case with only one installation (only venting emitters),
    # compared to the multi-installation case with two installations. The fuel-consumer installation should
    # give no CH4-contribution (only CO2)
    emissions_ch4_asset = get_sum_ltp_column(asset_ltp_result, installation_nr=0, ltp_column="storageCh4Mass")
    assert emissions_ch4 == emissions_ch4_asset


def test_power_from_shore(
    el_consumer_direct_base_load,
    fuel_gas,
    resource_service_factory,
    generator_electricity2fuel_17MW_resource,
    onshore_power_electricity2fuel_resource,
    cable_loss_time_series_resource,
):
    """Test power from shore output for LTP export."""

    time_vector_yearly = pd.date_range(datetime(2025, 1, 1), datetime(2031, 1, 1), freq="YS").to_pydatetime().tolist()
    fuel = fuel_gas(["co2", "ch4", "nmvoc", "nox"], [co2_factor, ch4_factor, nmvoc_factor, nox_factor])

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
        .with_fuel(fuel.name)
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
        fuel_types=[fuel],
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
        .with_fuel(fuel.name)
        .with_generator_sets([generator_set_csv])
        .with_regularity(regularity)
    ).validate()

    asset_pfs_csv = get_asset_yaml_model(
        installations=[installation_pfs_csv],
        fuel_types=[fuel],
        time_vector=time_vector_yearly,
        time_series=[cable_loss_time_series],
        facility_inputs=[generator_energy_function, power_from_shore_energy_function],
        frequency=Frequency.YEAR,
        resource_service=resource_service,
    )

    ltp_result = get_ltp_result(asset_pfs, asset_pfs.variables)
    ltp_result_csv = get_ltp_result(asset_pfs_csv, asset_pfs_csv.variables)

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
