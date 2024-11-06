from datetime import datetime
from pathlib import Path
from typing import Union

import pandas as pd
import pytest

from libecalc import dto
from libecalc.application.energy_calculator import EnergyCalculator
from libecalc.application.graph_result import GraphResult
from libecalc.common.time_utils import Frequency, Period, calculate_delta_days
from libecalc.common.units import Unit
from libecalc.common.utils.rates import RateType
from libecalc.common.variables import VariablesMap
from libecalc.fixtures.cases import ltp_export, venting_emitters
from libecalc.fixtures.cases.ltp_export.installation_setup import (
    expected_boiler_fuel_consumption,
    expected_ch4_from_diesel,
    expected_co2_from_boiler,
    expected_co2_from_diesel,
    expected_co2_from_fuel,
    expected_co2_from_heater,
    expected_diesel_consumption,
    expected_fuel_consumption,
    expected_gas_turbine_compressor_el_consumption,
    expected_gas_turbine_el_generated,
    expected_heater_fuel_consumption,
    expected_nmvoc_from_diesel,
    expected_nox_from_diesel,
    expected_offshore_wind_el_consumption,
    expected_pfs_el_consumption,
    installation_boiler_heater_dto,
    installation_compressor_dto,
    installation_diesel_fixed_dto,
    installation_diesel_mobile_dto,
    installation_direct_consumer_dto,
    installation_offshore_wind_dto,
    no_el_consumption,
    simple_direct_el_consumer,
)
from libecalc.fixtures.cases.ltp_export.loading_storage_ltp_yaml import (
    ltp_oil_loaded_yaml_factory,
)
from libecalc.fixtures.cases.ltp_export.utilities import (
    get_consumption,
    get_sum_ltp_column,
)
from libecalc.fixtures.cases.venting_emitters.venting_emitter_yaml import (
    venting_emitter_yaml_factory,
)
from libecalc.presentation.json_result.mapper import get_asset_result
from libecalc.presentation.json_result.result import EcalcModelResult
from libecalc.presentation.yaml.model import YamlModel
from libecalc.presentation.yaml.model_validation_exception import ModelValidationException
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_types.yaml_stream_conditions import (
    YamlEmissionRateUnits,
)

time_vector_installation = [
    datetime(2027, 1, 1),
    datetime(2027, 4, 10),
    datetime(2028, 1, 1),
    datetime(2028, 4, 10),
    datetime(2029, 1, 1),
]

time_vector_yearly = pd.date_range(datetime(2027, 1, 1), datetime(2029, 1, 1), freq="YS").to_pydatetime().tolist()


def calculate_asset_result(
    model: Union[dto.Installation, dto.Asset],
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


def test_emissions_diesel_fixed_and_mobile():
    """Test reporting of CH4 from diesel in LTP."""
    installation_fixed = installation_diesel_fixed_dto()
    installation_mobile = installation_diesel_mobile_dto()

    asset = dto.Asset(
        name="multiple_installations_asset",
        installations=[
            installation_fixed,
            installation_mobile,
        ],
    )

    variables = VariablesMap(time_vector=time_vector_installation, variables={"RATE": [1, 1, 1, 1]})

    ltp_result = get_consumption(model=asset, variables=variables, periods=variables.get_periods())

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


def test_temporal_models_detailed():
    """Test various queries for LTP reporting. Purpose: ensure that variations in temporal models are captured.

    Detailed temporal models (variations within one year) for:
    - Fuel type
    - Generator set user defined category
    - Generator set model
    """
    variables = VariablesMap(time_vector=time_vector_installation, variables={"RATE": [1, 1, 1, 1]})

    ltp_result = get_consumption(
        model=installation_direct_consumer_dto(), variables=variables, periods=variables.get_periods()
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


def test_temporal_models_offshore_wind():
    """Test ElConsumerPowerConsumptionQuery for calculating offshore wind el-consumption, LTP.

    Detailed temporal models (variations within one year) for:
    - El-consumer user defined category
    - El-consumer energy usage model
    """
    variables = VariablesMap(time_vector=time_vector_installation, variables={"RATE": [1, 1, 1, 1]})

    ltp_result = get_consumption(
        model=installation_offshore_wind_dto(), variables=variables, periods=variables.get_periods()
    )

    offshore_wind_el_consumption = get_sum_ltp_column(
        ltp_result, installation_nr=0, ltp_column="offshoreWindConsumption"
    )

    # ElConsumerPowerConsumptionQuery: Check that offshore wind el-consumption is correct.
    assert offshore_wind_el_consumption == expected_offshore_wind_el_consumption()


def test_temporal_models_compressor():
    """Test FuelConsumerPowerConsumptionQuery for calculating gas turbine compressor el-consumption, LTP.

    Detailed temporal models (variations within one year) for:
    - Fuel consumer user defined category
    """
    variables = VariablesMap(time_vector=time_vector_installation, variables={})

    ltp_result = get_consumption(
        model=installation_compressor_dto([no_el_consumption()]), variables=variables, periods=variables.get_periods()
    )

    gas_turbine_compressor_el_consumption = get_sum_ltp_column(
        ltp_result, installation_nr=0, ltp_column="gasTurbineCompressorConsumption"
    )

    # FuelConsumerPowerConsumptionQuery. Check gas turbine compressor el consumption.
    assert gas_turbine_compressor_el_consumption == expected_gas_turbine_compressor_el_consumption()


def test_boiler_heater_categories():
    variables = VariablesMap(time_vector=time_vector_installation, variables={})

    ltp_result = get_consumption(
        model=installation_boiler_heater_dto(), variables=variables, periods=variables.get_periods()
    )

    boiler_fuel_consumption = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column="boilerFuelGasConsumption")
    heater_fuel_consumption = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column="heaterFuelGasConsumption")
    co2_from_boiler = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column="boilerFuelGasCo2Mass")
    co2_from_heater = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column="heaterFuelGasCo2Mass")

    # FuelConsumerPowerConsumptionQuery. Check gas turbine compressor el consumption.
    assert boiler_fuel_consumption == expected_boiler_fuel_consumption()
    assert heater_fuel_consumption == expected_heater_fuel_consumption()
    assert co2_from_boiler == expected_co2_from_boiler()
    assert co2_from_heater == expected_co2_from_heater()


def test_venting_emitters():
    """Test venting emitters for LTP export.

    Verify correct behaviour if input rate is given in different units and rate types (sd and cd).
    """
    time_vector = [
        datetime(2027, 1, 1),
        datetime(2028, 1, 1),
    ]
    regularity = 0.2
    emission_rate = 10

    variables = VariablesMap(time_vector=time_vector, variables={})

    dto_sd_kg_per_day = venting_emitter_yaml_factory(
        emission_rates=[emission_rate],
        regularity=regularity,
        units=[YamlEmissionRateUnits.KILO_PER_DAY],
        emission_names=["ch4"],
        rate_types=[RateType.STREAM_DAY],
        names=["Venting emitter 1"],
        path=Path(venting_emitters.__path__[0]),
    )

    dto_sd_tons_per_day = venting_emitter_yaml_factory(
        emission_rates=[emission_rate],
        regularity=regularity,
        rate_types=[RateType.STREAM_DAY],
        units=[YamlEmissionRateUnits.TONS_PER_DAY],
        emission_names=["ch4"],
        names=["Venting emitter 1"],
        path=Path(venting_emitters.__path__[0]),
    )

    dto_cd_kg_per_day = venting_emitter_yaml_factory(
        emission_rates=[emission_rate],
        regularity=regularity,
        rate_types=[RateType.CALENDAR_DAY],
        units=[YamlEmissionRateUnits.KILO_PER_DAY],
        emission_names=["ch4"],
        names=["Venting emitter 1"],
        path=Path(venting_emitters.__path__[0]),
    )

    ltp_result_input_sd_kg_per_day = get_consumption(
        model=dto_sd_kg_per_day.ecalc_model, variables=variables, periods=variables.get_periods()
    )

    ltp_result_input_sd_tons_per_day = get_consumption(
        model=dto_sd_tons_per_day.ecalc_model, variables=variables, periods=variables.get_periods()
    )

    ltp_result_input_cd_kg_per_day = get_consumption(
        model=dto_cd_kg_per_day.ecalc_model, variables=variables, periods=variables.get_periods()
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


def test_only_venting_emitters_no_fuelconsumers():
    """
    Test that it is possible with only venting emitters, without fuelconsumers.
    """
    time_vector = [
        datetime(2027, 1, 1),
        datetime(2028, 1, 1),
    ]
    regularity = 0.2
    emission_rate = 10

    variables = VariablesMap(time_vector=time_vector, variables={})

    # Installation with only venting emitters:
    dto_case_emitters = venting_emitter_yaml_factory(
        emission_rates=[emission_rate],
        regularity=regularity,
        units=[YamlEmissionRateUnits.KILO_PER_DAY],
        emission_names=["ch4"],
        rate_types=[RateType.STREAM_DAY],
        include_emitters=True,
        include_fuel_consumers=False,
        names=["Venting emitter 1"],
        installation_name="Venting emitter installation",
        path=Path(venting_emitters.__path__[0]),
    )

    venting_emitter_results = get_consumption(
        model=dto_case_emitters.ecalc_model, variables=variables, periods=variables.get_periods()
    )

    # Verify that eCalc is not failing in get_asset_result with only venting emitters -
    # when installation result is empty, i.e. with no genset and fuel consumers:
    assert isinstance(
        calculate_asset_result(model=dto_case_emitters.ecalc_model, variables=variables), EcalcModelResult
    )

    # Verify correct emissions:
    emissions_ch4 = get_sum_ltp_column(venting_emitter_results, installation_nr=0, ltp_column="storageCh4Mass")
    assert emissions_ch4 == (emission_rate / 1000) * 365 * regularity

    # Installation with only fuel consumers:
    dto_case_fuel = venting_emitter_yaml_factory(
        emission_rates=[emission_rate],
        regularity=regularity,
        units=[YamlEmissionRateUnits.KILO_PER_DAY],
        emission_names=["ch4"],
        rate_types=[RateType.STREAM_DAY],
        include_emitters=False,
        include_fuel_consumers=True,
        names=["Venting emitter 1"],
        installation_name="Fuel consumer installation",
        path=Path(venting_emitters.__path__[0]),
    )

    asset_multi_installations = dto.Asset(
        name="Multi installations",
        installations=[dto_case_emitters.ecalc_model.installations[0], dto_case_fuel.ecalc_model.installations[0]],
    )

    # Verify that eCalc is not failing in get_asset_result, with only venting emitters -
    # when installation result is empty for one installation, i.e. with no genset and fuel consumers.
    # Include asset with two installations, one with only emitters and one with only fuel consumers -
    # ensure that get_asset_result returns a result:

    assert isinstance(calculate_asset_result(model=asset_multi_installations, variables=variables), EcalcModelResult)

    asset_ltp_result = get_consumption(
        model=asset_multi_installations, variables=variables, periods=variables.get_periods()
    )
    # Check that the results are the same: For the case with only one installation (only venting emitters),
    # compared to the multi-installation case with two installations. The fuel-consumer installation should
    # give no CH4-contribution (only CO2)
    emissions_ch4_asset = get_sum_ltp_column(asset_ltp_result, installation_nr=0, ltp_column="storageCh4Mass")
    assert emissions_ch4 == emissions_ch4_asset


def test_no_emitters_or_fuelconsumers(
    yaml_asset_builder_factory,
    yaml_installation_builder_factory,
    yaml_asset_configuration_service_factory,
    resource_service_factory,
):
    """
    Test that eCalc returns error when neither fuelconsumers or venting emitters are specified.
    """
    asset = (
        yaml_asset_builder_factory()
        .with_test_data()
        .with_installations(
            [
                yaml_installation_builder_factory()
                .with_test_data()
                .with_name("this_is_the_name_we_want_in_the_error")
                .with_fuel_consumers([])
                .with_venting_emitters([])
                .with_generator_sets([])
                .construct()
            ]
        )
        .construct()
    )
    configuration_service = yaml_asset_configuration_service_factory(asset, "no consumers or emitters")
    model = YamlModel(
        configuration_service=configuration_service,
        resource_service=resource_service_factory({}),
        output_frequency=Frequency.NONE,
    )

    with pytest.raises(ModelValidationException) as ee:
        model.validate_for_run()

    error_message = str(ee.value)
    assert "this_is_the_name_we_want_in_the_error" in error_message
    assert f"It is required to specify at least one of the keywords {EcalcYamlKeywords.fuel_consumers}, {EcalcYamlKeywords.generator_sets} or {EcalcYamlKeywords.installation_venting_emitters} in the model."


def test_total_oil_loaded_old_method():
    """Test total oil loaded/stored for LTP export. Using original method where direct/venting emitters are
    modelled as FUELSCONSUMERS using DIRECT.

    Verify correct volume when model includes emissions related to both storage and loading of oil,
    and when model includes only loading.
    """
    time_vector = [
        datetime(2027, 1, 1),
        datetime(2028, 1, 1),
    ]
    variables = VariablesMap(time_vector=time_vector, variables={})

    regularity = 0.6
    emission_factor = 2
    fuel_rate = 100

    # Create model with both loading and storage
    asset_loading_storage = ltp_oil_loaded_yaml_factory(
        emission_factor=emission_factor,
        rate_types=[RateType.STREAM_DAY, RateType.STREAM_DAY],
        fuel_rates=[fuel_rate, fuel_rate],
        emission_name="ch4",
        regularity=regularity,
        categories=["LOADING", "STORAGE"],
        consumer_names=["loading", "storage"],
    )

    # Create model with only loading, not storage
    asset_loading_only = ltp_oil_loaded_yaml_factory(
        emission_factor=emission_factor,
        rate_types=[RateType.STREAM_DAY],
        fuel_rates=[fuel_rate],
        emission_name="ch4",
        regularity=regularity,
        categories=["LOADING"],
        consumer_names=["loading"],
    )

    ltp_result_loading_storage = get_consumption(
        model=asset_loading_storage, variables=variables, periods=variables.get_periods()
    )
    ltp_result_loading_only = get_consumption(
        model=asset_loading_only, variables=variables, periods=variables.get_periods()
    )

    loaded_and_stored_oil_loading_and_storage = get_sum_ltp_column(
        ltp_result_loading_storage, installation_nr=0, ltp_column="loadedAndStoredOil"
    )
    loaded_and_stored_oil_loading_only = get_sum_ltp_column(
        ltp_result_loading_only, installation_nr=0, ltp_column="loadedAndStoredOil"
    )

    # Verify output for total oil loaded/stored, if only loading is specified.
    assert loaded_and_stored_oil_loading_only is not None

    # Verify correct volume for oil loaded/stored
    assert loaded_and_stored_oil_loading_and_storage == fuel_rate * 365 * regularity

    # Verify that total oil loaded/stored is the same if only loading is specified,
    # compared to a model with both loading and storage.
    assert loaded_and_stored_oil_loading_and_storage == loaded_and_stored_oil_loading_only


def test_electrical_and_mechanical_power_installation():
    """Check that new total power includes the sum of electrical- and mechanical power at installation level"""
    variables = VariablesMap(time_vector=time_vector_installation, variables={})
    asset = dto.Asset(
        name="Asset 1",
        installations=[
            installation_compressor_dto([simple_direct_el_consumer()]),
        ],
    )

    asset_result = calculate_asset_result(model=asset, variables=variables)
    power_fuel_driven_compressor = asset_result.get_component_by_name("compressor").power_cumulative.values[-1]
    power_generator_set = asset_result.get_component_by_name("genset").power_cumulative.values[-1]

    # Extract cumulative electrical-, mechanical- and total power.
    power_electrical_installation = asset_result.get_component_by_name(
        "INSTALLATION_A"
    ).power_electrical_cumulative.values[-1]

    power_mechanical_installation = asset_result.get_component_by_name(
        "INSTALLATION_A"
    ).power_mechanical_cumulative.values[-1]

    power_total_installation = asset_result.get_component_by_name("INSTALLATION_A").power_cumulative.values[-1]

    # Verify that total power is correct
    assert power_total_installation == power_electrical_installation + power_mechanical_installation

    # Verify that electrical power equals genset power, and mechanical power equals power from gas driven compressor:
    assert power_generator_set == power_electrical_installation
    assert power_fuel_driven_compressor == power_mechanical_installation


def test_electrical_and_mechanical_power_asset():
    """Check that new total power includes the sum of electrical- and mechanical power at installation level"""
    variables = VariablesMap(time_vector=time_vector_installation, variables={})
    installation_name_1 = "INSTALLATION_1"
    installation_name_2 = "INSTALLATION_2"

    asset = dto.Asset(
        name="Asset 1",
        installations=[
            installation_compressor_dto(
                [simple_direct_el_consumer(name="direct_el_consumer 1")],
                installation_name=installation_name_1,
                genset_name="generator 1",
                compressor_name="gas driven compressor 1",
            ),
            installation_compressor_dto(
                [simple_direct_el_consumer(name="direct_el_consumer 2")],
                installation_name=installation_name_2,
                genset_name="generator 2",
                compressor_name="gas driven compressor 2",
            ),
        ],
    )

    asset_result = calculate_asset_result(model=asset, variables=variables)
    power_electrical_installation_1 = asset_result.get_component_by_name(
        installation_name_1
    ).power_electrical_cumulative.values[-1]

    power_mechanical_installation_1 = asset_result.get_component_by_name(
        installation_name_1
    ).power_mechanical_cumulative.values[-1]

    power_electrical_installation_2 = asset_result.get_component_by_name(
        installation_name_2
    ).power_electrical_cumulative.values[-1]

    power_mechanical_installation_2 = asset_result.get_component_by_name(
        installation_name_2
    ).power_mechanical_cumulative.values[-1]

    asset_power_electrical = asset_result.get_component_by_name("Asset 1").power_electrical_cumulative.values[-1]

    asset_power_mechanical = asset_result.get_component_by_name("Asset 1").power_mechanical_cumulative.values[-1]

    # Verify that electrical power is correct at asset level
    assert asset_power_electrical == power_electrical_installation_1 + power_electrical_installation_2

    # Verify that mechanical power is correct at asset level:
    assert asset_power_mechanical == power_mechanical_installation_1 + power_mechanical_installation_2


def test_power_from_shore(ltp_pfs_yaml_factory):
    """Test power from shore output for LTP export."""

    time_vector_yearly = pd.date_range(datetime(2025, 1, 1), datetime(2031, 1, 1), freq="YS").to_pydatetime().tolist()

    VariablesMap(time_vector=time_vector_yearly, variables={})
    regularity = 0.2
    load = 10
    cable_loss = 0.1
    max_from_shore = 12

    dto_case = ltp_pfs_yaml_factory(
        regularity=regularity,
        cable_loss=cable_loss,
        max_usage_from_shore=max_from_shore,
        load_direct_consumer=load,
        path=Path(ltp_export.__path__[0]),
    )

    dto_case.ecalc_model.model_validate(dto_case.ecalc_model)

    dto_case_csv = ltp_pfs_yaml_factory(
        regularity=regularity,
        cable_loss="CABLE_LOSS;CABLE_LOSS_FACTOR",
        max_usage_from_shore=max_from_shore,
        load_direct_consumer=load,
        path=Path(ltp_export.__path__[0]),
    )

    ltp_result = get_consumption(
        model=dto_case.ecalc_model, variables=dto_case.variables, periods=dto_case.variables.get_periods()
    )
    ltp_result_csv = get_consumption(
        model=dto_case_csv.ecalc_model, variables=dto_case.variables, periods=dto_case.variables.get_periods()
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
    assert ltp_result.query_results[0].query_results[3].unit == Unit.MEGA_WATT


def test_max_usage_from_shore(ltp_pfs_yaml_factory):
    """Test power from shore output for LTP export."""

    regularity = 0.2
    load = 10
    cable_loss = 0.1

    dto_case_csv = ltp_pfs_yaml_factory(
        regularity=regularity,
        cable_loss=cable_loss,
        max_usage_from_shore="MAX_USAGE_FROM_SHORE;MAX_USAGE_FROM_SHORE",
        load_direct_consumer=load,
        path=Path(ltp_export.__path__[0]),
    )

    ltp_result_csv = get_consumption(
        model=dto_case_csv.ecalc_model, variables=dto_case_csv.variables, periods=dto_case_csv.variables.get_periods()
    )

    max_usage_from_shore_2027 = float(
        ltp_result_csv.query_results[0].query_results[3].values[Period(datetime(2027, 1, 1), datetime(2028, 1, 1))]
    )

    # In the input csv-file max usage from shore is 250 (1.12.2026), 290 (1.6.2027), 283 (1.1.2028)
    # and 283 (1.1.2029). Ensure that the correct value is set for 2027 (290 from 1.6):
    assert max_usage_from_shore_2027 == 290.0

    # Ensure that values in 2027, 2028 and 2029 are correct, based on input file:
    assert [float(max_pfs) for max_pfs in ltp_result_csv.query_results[0].query_results[3].values.values()][2:5] == [
        290,
        283,
        283,
    ]
