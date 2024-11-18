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
)
from tests.libecalc.presentation.exporter.conftest import (
    get_yaml_model,
    get_consumption,
    get_sum_ltp_column,
    expected_boiler_fuel_consumption,
    expected_heater_fuel_consumption,
    expected_co2_from_boiler,
    expected_co2_from_heater,
    get_asset_yaml_model,
    calculate_asset_result,
    get_ltp_column,
    generator_fuel_power_to_fuel_data,
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
    regularity_temporal_installation,
    category_dict,
)

from tests.libecalc.presentation.exporter.memory_resources import (
    generator_electricity2fuel_17MW_resource,
    onshore_power_electricity2fuel_resource,
    cable_loss_time_series_resource,
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

time_vector_installation = [
    date1,
    date2,
    date3,
    date4,
    date5,
]

period_from_date1 = Period(date1)
period_from_date3 = Period(date3)

fuel_rate = 67000
power_usage_mw = 10
diesel_rate = 120000
regularity_installation = 1.0
load_consumer = 10


def test_emissions_diesel_fixed_and_mobile(
    generator_diesel_power_to_fuel_data,
    generator_fuel_power_to_fuel_data,
    generator_set_temporal_dict,
    el_consumer_direct_base_load,
    resource_service_factory,
    fuel_multi_temporal,
    fuel_turbine,
    fuel_diesel_multi,
):
    """Test reporting of CH4 from diesel in LTP."""

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
            generator_set_temporal_dict(
                generator_reference1=generator_diesel_energy_function.name,
                generator_reference2=generator_fuel_energy_function.name,
            )
        )
    ).validate()

    generator_mobile = deepcopy(generator_fixed)
    generator_mobile.name = "generator_mobile"

    installation_fixed = (
        YamlInstallationBuilder()
        .with_name("INSTALLATION_FIXED")
        .with_regularity(regularity_installation)
        .with_fuel(fuel_multi_temporal(fuel_diesel_multi, fuel_turbine))
        .with_category(InstallationUserDefinedCategoryType.FIXED)
        .with_generator_sets([generator_fixed])
    ).validate()

    installation_mobile = (
        YamlInstallationBuilder()
        .with_name("INSTALLATION_MOBILE")
        .with_regularity(regularity_installation)
        .with_fuel(fuel_multi_temporal(fuel_diesel_multi, fuel_turbine))
        .with_category(InstallationUserDefinedCategoryType.MOBILE)
        .with_generator_sets([generator_mobile])
    ).validate()

    resources = {
        generator_diesel_energy_function.name: generator_diesel_power_to_fuel_data,
        generator_fuel_energy_function.name: generator_fuel_power_to_fuel_data,
    }
    resource_service = resource_service_factory(resources=resources)

    asset = get_asset_yaml_model(
        installations=[installation_fixed, installation_mobile],
        fuel_types=[fuel_turbine, fuel_diesel_multi],
        time_vector=time_vector_installation,
        facility_inputs=[generator_diesel_energy_function, generator_fuel_energy_function],
        frequency=Frequency.YEAR,
        resource_service=resource_service,
    )

    variables_map = VariablesMap(time_vector=time_vector_installation, variables={"RATE": [1, 1, 1, 1]})

    ltp_result = get_consumption(
        model=asset, variables_map=variables_map, periods=variables_map.get_periods(), frequency=Frequency.YEAR
    )

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

    assert co2_from_diesel_fixed == expected_co2_from_diesel()
    assert co2_from_diesel_mobile == expected_co2_from_diesel()
    assert nox_from_diesel_fixed == expected_nox_from_diesel()
    assert nox_from_diesel_mobile == expected_nox_from_diesel()
    assert nmvoc_from_diesel_fixed == expected_nmvoc_from_diesel()
    assert nmvoc_from_diesel_mobile == expected_nmvoc_from_diesel()
    assert ch4_from_diesel_fixed == expected_ch4_from_diesel()
    assert ch4_from_diesel_mobile == expected_ch4_from_diesel()


def test_temporal_models_detailed(
    generator_set_temporal_dict,
    fuel_multi_temporal,
    diesel_turbine,
    fuel_turbine,
    generator_diesel_power_to_fuel_data,
    generator_fuel_power_to_fuel_data,
    resource_service_factory,
    el_consumer_direct_base_load,
):
    """Test various queries for LTP reporting. Purpose: ensure that variations in temporal models are captured.

    Detailed temporal models (variations within one year) for:
    - Fuel type
    - Generator set user defined category
    - Generator set model
    """
    variables_map = VariablesMap(time_vector=time_vector_installation, variables={"RATE": [1, 1, 1, 1]})

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
            generator_set_temporal_dict(
                generator_reference1=generator_diesel_energy_function.name,
                generator_reference2=generator_fuel_energy_function.name,
            )
        )
    ).validate()

    installation = (
        YamlInstallationBuilder()
        .with_name("INSTALLATION A")
        .with_generator_sets([generator_set])
        .with_fuel(fuel_multi_temporal(fuel1=diesel_turbine, fuel2=fuel_turbine))
        .with_category(InstallationUserDefinedCategoryType.FIXED)
    ).validate()

    resources = {
        generator_diesel_energy_function.name: generator_diesel_power_to_fuel_data,
        generator_fuel_energy_function.name: generator_fuel_power_to_fuel_data,
    }
    resource_service = resource_service_factory(resources=resources)

    asset = get_asset_yaml_model(
        installations=[installation],
        fuel_types=[fuel_turbine, diesel_turbine],
        time_vector=time_vector_installation,
        facility_inputs=[generator_diesel_energy_function, generator_fuel_energy_function],
        frequency=Frequency.YEAR,
        resource_service=resource_service,
    )

    ltp_result = get_consumption(
        model=asset, variables_map=variables_map, periods=variables_map.get_periods(), frequency=Frequency.YEAR
    )

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
    assert turbine_fuel_consumption == expected_fuel_consumption()

    # FuelQuery: Check that turbine fuel gas is not categorized as diesel,
    # even if the temporal model starts with diesel every year
    assert engine_diesel_consumption != expected_diesel_consumption() + expected_fuel_consumption()

    # FuelQuery: Check that diesel consumption is correct
    assert engine_diesel_consumption == pytest.approx(expected_diesel_consumption(), 0.00001)

    # ElectricityGeneratedQuery: Check that turbine power generation is correct.
    assert gas_turbine_el_generated == pytest.approx(expected_gas_turbine_el_generated(), 0.00001)

    # ElectricityGeneratedQuery: Check that power from shore el consumption is correct.
    assert pfs_el_consumption == pytest.approx(expected_pfs_el_consumption(), 0.00001)

    # EmissionQuery. Check that co2 from fuel is correct.
    assert co2_from_fuel == expected_co2_from_fuel()

    # EmissionQuery: Emissions. Check that co2 from diesel is correct.
    assert co2_from_diesel == expected_co2_from_diesel()


def test_temporal_models_offshore_wind(
    el_consumer_direct_base_load,
    offshore_wind_consumer,
    fuel_turbine,
    generator_fuel_power_to_fuel_data,
    resource_service_factory,
):
    """Test ElConsumerPowerConsumptionQuery for calculating offshore wind el-consumption, LTP.

    Detailed temporal models (variations within one year) for:
    - El-consumer user defined category
    - El-consumer energy usage model
    """
    variables_map = VariablesMap(time_vector=time_vector_installation, variables={"RATE": [1, 1, 1, 1]})

    generator_fuel_energy_function = (
        YamlElectricity2fuelBuilder()
        .with_name("generator_fuel_energy_function")
        .with_file("generator_fuel_energy_function")
    ).validate()

    generator_set = (
        YamlGeneratorSetBuilder()
        .with_name("generator_set")
        .with_category({period_from_date1.start: ConsumerUserDefinedCategoryType.TURBINE_GENERATOR})
        .with_consumers([offshore_wind_consumer])
        .with_electricity2fuel({period_from_date1.start: generator_fuel_energy_function.name})
    ).validate()

    installation = (
        YamlInstallationBuilder()
        .with_name("INSTALLATION A")
        .with_generator_sets([generator_set])
        .with_fuel(fuel_turbine.name)
        .with_category(InstallationUserDefinedCategoryType.FIXED)
    ).validate()

    resources = {
        generator_fuel_energy_function.name: generator_fuel_power_to_fuel_data,
    }

    resource_service = resource_service_factory(resources=resources)

    asset = get_asset_yaml_model(
        installations=[installation],
        fuel_types=[fuel_turbine],
        time_vector=time_vector_installation,
        facility_inputs=[generator_fuel_energy_function],
        frequency=Frequency.YEAR,
        resource_service=resource_service,
    )

    ltp_result = get_consumption(
        model=asset, variables_map=variables_map, periods=variables_map.get_periods(), frequency=Frequency.YEAR
    )

    offshore_wind_el_consumption = get_sum_ltp_column(
        ltp_result, installation_nr=0, ltp_column="offshoreWindConsumption"
    )

    # ElConsumerPowerConsumptionQuery: Check that offshore wind el-consumption is correct.
    assert offshore_wind_el_consumption == expected_offshore_wind_el_consumption()


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
        installations=[installation_sd_kg_per_day],
        fuel_types=[fuel_turbine],
        time_vector=time_vector,
        frequency=Frequency.YEAR,
    )

    asset_sd_tons_per_day = get_asset_yaml_model(
        installations=[installation_sd_tons_per_day],
        fuel_types=[fuel_turbine],
        time_vector=time_vector,
        frequency=Frequency.YEAR,
    )

    asset_cd_kg_per_day = get_asset_yaml_model(
        installations=[installation_cd_kg_per_day],
        fuel_types=[fuel_turbine],
        time_vector=time_vector,
        frequency=Frequency.YEAR,
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
        .with_fuel_consumers([fuel_consumer_direct(fuel_reference_name=fuel_turbine.name, rate=fuel_rate)])
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
