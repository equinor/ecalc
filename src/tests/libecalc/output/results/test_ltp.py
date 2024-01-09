from datetime import datetime
from typing import Union

import pandas as pd
import pytest
from libecalc import dto
from libecalc.application.energy_calculator import EnergyCalculator
from libecalc.application.graph_result import GraphResult
from libecalc.common.time_utils import Frequency
from libecalc.common.units import Unit
from libecalc.common.utils.rates import RateType
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
)
from libecalc.fixtures.cases.ltp_export.loading_storage_ltp_yaml import (
    ltp_oil_loaded_yaml_factory,
)
from libecalc.fixtures.cases.venting_emitters.venting_emitter_yaml import (
    venting_emitter_yaml_factory,
)
from libecalc.presentation.exporter.configs.configs import LTPConfig

time_vector_installation = [
    datetime(2027, 1, 1),
    datetime(2027, 4, 10),
    datetime(2028, 1, 1),
    datetime(2028, 4, 10),
    datetime(2029, 1, 1),
]

time_vector_yearly = pd.date_range(datetime(2027, 1, 1), datetime(2029, 1, 1), freq="YS").to_pydatetime().tolist()


def get_consumption(model: Union[dto.Installation, dto.Asset], variables: dto.VariablesMap):
    model = model
    graph = model.get_graph()
    energy_calculator = EnergyCalculator(graph=graph)

    consumer_results = energy_calculator.evaluate_energy_usage(variables)
    emission_results = energy_calculator.evaluate_emissions(variables, consumer_results)

    graph_result = GraphResult(
        graph=graph,
        variables_map=variables,
        consumer_results=consumer_results,
        emission_results=emission_results,
    )

    ltp_filter = LTPConfig.filter(frequency=Frequency.YEAR)
    ltp_result = ltp_filter.filter(graph_result, time_vector_yearly)

    return ltp_result


def get_sum_ltp_column(ltp_result, installation_nr, ltp_column_nr) -> float:
    ltp_sum = sum(
        float(v) for (k, v) in ltp_result.query_results[installation_nr].query_results[ltp_column_nr].values.items()
    )
    return ltp_sum


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

    variables = dto.VariablesMap(time_vector=time_vector_installation, variables={"RATE": [1, 1, 1, 1, 1, 1]})

    ltp_result = get_consumption(model=asset, variables=variables)

    co2_from_diesel_fixed = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column_nr=1)
    co2_from_diesel_mobile = get_sum_ltp_column(ltp_result, installation_nr=1, ltp_column_nr=1)

    nox_from_diesel_fixed = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column_nr=2)
    nox_from_diesel_mobile = get_sum_ltp_column(ltp_result, installation_nr=1, ltp_column_nr=2)

    nmvoc_from_diesel_fixed = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column_nr=3)
    nmvoc_from_diesel_mobile = get_sum_ltp_column(ltp_result, installation_nr=1, ltp_column_nr=3)

    ch4_from_diesel_fixed = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column_nr=4)
    ch4_from_diesel_mobile = get_sum_ltp_column(ltp_result, installation_nr=1, ltp_column_nr=4)

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
    variables = dto.VariablesMap(time_vector=time_vector_installation, variables={"RATE": [1, 1, 1, 1, 1, 1]})

    ltp_result = get_consumption(model=installation_direct_consumer_dto(), variables=variables)

    turbine_fuel_consumption = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column_nr=0)
    engine_diesel_consumption = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column_nr=1)

    gas_turbine_el_generated = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column_nr=4)
    pfs_el_consumption = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column_nr=5)

    co2_from_fuel = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column_nr=2)
    co2_from_diesel = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column_nr=3)

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
    variables = dto.VariablesMap(time_vector=time_vector_installation, variables={"RATE": [1, 1, 1, 1, 1, 1]})

    ltp_result = get_consumption(model=installation_offshore_wind_dto(), variables=variables)

    offshore_wind_el_consumption = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column_nr=3)

    # ElConsumerPowerConsumptionQuery: Check that offshore wind el-consumption is correct.
    assert offshore_wind_el_consumption == expected_offshore_wind_el_consumption()


def test_temporal_models_compressor():
    """Test FuelConsumerPowerConsumptionQuery for calculating gas turbine compressor el-consumption, LTP.

    Detailed temporal models (variations within one year) for:
    - Fuel consumer user defined category
    """
    variables = dto.VariablesMap(time_vector=time_vector_installation, variables={})

    ltp_result = get_consumption(model=installation_compressor_dto(), variables=variables)

    gas_turbine_compressor_el_consumption = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column_nr=3)

    # FuelConsumerPowerConsumptionQuery. Check gas turbine compressor el consumption.
    assert gas_turbine_compressor_el_consumption == expected_gas_turbine_compressor_el_consumption()


def test_boiler_heater_categories():
    variables = dto.VariablesMap(time_vector=time_vector_installation, variables={})

    ltp_result = get_consumption(model=installation_boiler_heater_dto(), variables=variables)

    boiler_fuel_consumption = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column_nr=0)
    heater_fuel_consumption = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column_nr=1)
    co2_from_boiler = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column_nr=2)
    co2_from_heater = get_sum_ltp_column(ltp_result, installation_nr=0, ltp_column_nr=3)

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

    variables = dto.VariablesMap(time_vector=time_vector, variables={})

    installation_sd_kg_per_day = venting_emitter_yaml_factory(
        emission_rate=emission_rate,
        regularity=regularity,
        unit=Unit.KILO_PER_DAY,
        emission_name="ch4",
        rate_type=RateType.STREAM_DAY,
    )

    installation_sd_tons_per_day = venting_emitter_yaml_factory(
        emission_rate=emission_rate,
        regularity=regularity,
        rate_type=RateType.STREAM_DAY,
        unit=Unit.TONS_PER_DAY,
        emission_name="ch4",
    )

    installation_cd_kg_per_day = venting_emitter_yaml_factory(
        emission_rate=emission_rate,
        regularity=regularity,
        rate_type=RateType.CALENDAR_DAY,
        unit=Unit.KILO_PER_DAY,
        emission_name="ch4",
    )

    ltp_result_input_sd_kg_per_day = get_consumption(model=installation_sd_kg_per_day, variables=variables)

    ltp_result_input_sd_tons_per_day = get_consumption(model=installation_sd_tons_per_day, variables=variables)

    ltp_result_input_cd_kg_per_day = get_consumption(model=installation_cd_kg_per_day, variables=variables)

    emission_input_sd_kg_per_day = get_sum_ltp_column(
        ltp_result_input_sd_kg_per_day, installation_nr=0, ltp_column_nr=0
    )
    emission_input_sd_tons_per_day = get_sum_ltp_column(
        ltp_result_input_sd_tons_per_day, installation_nr=0, ltp_column_nr=0
    )
    emission_input_cd_kg_per_day = get_sum_ltp_column(
        ltp_result_input_cd_kg_per_day, installation_nr=0, ltp_column_nr=0
    )

    # Verify correct emissions when input is kg per day. Output should be in tons per day - hence dividing by 1000
    assert emission_input_sd_kg_per_day == (emission_rate / 1000) * 365 * regularity

    # Verify correct emissions when input is tons per day.
    assert emission_input_sd_tons_per_day == emission_rate * 365 * regularity

    # Verify that input calendar day vs input stream day is linked correctly through regularity
    assert emission_input_cd_kg_per_day == emission_input_sd_kg_per_day / regularity

    # Verify that results is independent of regularity, when input rate is in calendar days
    assert emission_input_cd_kg_per_day == (emission_rate / 1000) * 365


def test_total_oil_loaded():
    """Test total oil loaded/stored for LTP export.

    Verify correct volume when model includes emissions related to both storage and loading of oil,
    and when model includes only loading.
    """
    time_vector = [
        datetime(2027, 1, 1),
        datetime(2028, 1, 1),
    ]
    variables = dto.VariablesMap(time_vector=time_vector, variables={})

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

    ltp_result_loading_storage = get_consumption(model=asset_loading_storage, variables=variables)
    ltp_result_loading_only = get_consumption(model=asset_loading_only, variables=variables)

    loaded_and_stored_oil_loading_and_storage = get_sum_ltp_column(
        ltp_result_loading_storage, installation_nr=0, ltp_column_nr=2
    )
    loaded_and_stored_oil_loading_only = get_sum_ltp_column(ltp_result_loading_only, installation_nr=0, ltp_column_nr=1)

    # Verify output for total oil loaded/stored, if only loading is specified.
    assert loaded_and_stored_oil_loading_only is not None

    # Verify correct volume for oil loaded/stored
    assert loaded_and_stored_oil_loading_and_storage == fuel_rate * 365 * regularity

    # Verify that total oil loaded/stored is the same if only loading is specified,
    # compared to a model with both loading and storage.
    assert loaded_and_stored_oil_loading_and_storage == loaded_and_stored_oil_loading_only
