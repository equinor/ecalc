from copy import deepcopy
from datetime import datetime

import pandas as pd
import pytest

from libecalc.common.time_utils import Frequency, calculate_delta_days
from libecalc.common.units import Unit
from libecalc.common.utils.rates import RateType
from libecalc.common.variables import VariablesMap
from libecalc.dto.types import ConsumerUserDefinedCategoryType, InstallationUserDefinedCategoryType
from libecalc.presentation.json_result.result import EcalcModelResult
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

time_vector_installation = [
    date1,
    date2,
    date3,
    date4,
    date5,
]

fuel_rate = 67000


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
