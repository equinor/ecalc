from datetime import datetime
from typing import List

import pytest
from libecalc.application.energy_calculator import EnergyCalculator
from libecalc.application.graph_result import EcalcModelResult, GraphResult
from libecalc.common.component_info.compressor import CompressorPressureType
from libecalc.common.units import Unit
from libecalc.common.utils.rates import TimeSeriesFloat
from libecalc.presentation.json_result.mapper import (
    get_asset_result,
    get_requested_compressor_pressures,
)
from libecalc.presentation.json_result.result.results import CompressorModelResult


@pytest.fixture
def result(compressor_systems_and_compressor_train_temporal_dto) -> EcalcModelResult:
    ecalc_model = compressor_systems_and_compressor_train_temporal_dto.ecalc_model
    variables = compressor_systems_and_compressor_train_temporal_dto.variables

    graph = ecalc_model.get_graph()
    energy_calculator = EnergyCalculator(graph=graph)
    consumer_results = energy_calculator.evaluate_energy_usage(variables)
    emission_results = energy_calculator.evaluate_emissions(
        variables_map=variables,
        consumer_results=consumer_results,
    )

    result = get_asset_result(
        GraphResult(
            graph=graph,
            consumer_results=consumer_results,
            variables_map=variables,
            emission_results=emission_results,
        )
    )

    return result


def get_inlet_pressure(list_index: int, timestep: datetime, models: List[CompressorModelResult]) -> float:
    return models[list_index].requested_inlet_pressure.for_timestep(timestep).values[0]


def get_outlet_pressure(list_index: int, timestep: datetime, models: List[CompressorModelResult]) -> float:
    return models[list_index].requested_outlet_pressure.for_timestep(timestep).values[0]


def test_requested_pressures_compressor_train_temporal_model(result: EcalcModelResult):
    """
    Check requested inlet- and outlet pressures for compressor trains, using temporal models.

    :param result: eCalc result including models with requested pressures
    :return: Nothing
    """
    models = result.models

    simplified_variable_speed_compressor_train_known_stages_consumer_temporal_model_first = models[0]
    simplified_variable_speed_compressor_train_known_stages_consumer_temporal_model_second = models[1]

    assert (
        simplified_variable_speed_compressor_train_known_stages_consumer_temporal_model_first.requested_inlet_pressure
        == TimeSeriesFloat(timesteps=[datetime(2018, 1, 1, 0, 0)], values=[50.0], unit=Unit.BARA)
    )
    assert (
        simplified_variable_speed_compressor_train_known_stages_consumer_temporal_model_first.requested_outlet_pressure
        == TimeSeriesFloat(timesteps=[datetime(2018, 1, 1, 0, 0)], values=[250.0], unit=Unit.BARA)
    )

    assert (
        simplified_variable_speed_compressor_train_known_stages_consumer_temporal_model_second.requested_inlet_pressure
        == TimeSeriesFloat(
            timesteps=[datetime(2019, 1, 1, 0, 0), datetime(2020, 1, 1, 0, 0)], values=[40.0, 40.0], unit=Unit.BARA
        )
    )
    assert (
        simplified_variable_speed_compressor_train_known_stages_consumer_temporal_model_second.requested_outlet_pressure
        == TimeSeriesFloat(
            timesteps=[datetime(2019, 1, 1, 0, 0), datetime(2020, 1, 1, 0, 0)], values=[260.0, 260.0], unit=Unit.BARA
        )
    )


def test_requested_pressures_compressor_system_temporal_model(result: EcalcModelResult):
    """
    Check requested inlet- and outlet pressures for compressor systems.
    Use temporal models, different inlet/outlet pressures for each compressor in the system,
    and several priorities (operational settings).

    :param result: eCalc result including models with requested pressures
    :return: Nothing
    """
    date_temporal_1 = datetime(2018, 1, 1)
    date_temporal_2 = datetime(2019, 1, 1)
    models = result.models

    # Compressor system with temporal model and inlet/outlet pressures per compressor
    requested_inlet_pressure_train1 = get_inlet_pressure(2, date_temporal_1, models)
    requested_inlet_pressure_train1_upgr = get_inlet_pressure(3, date_temporal_2, models)
    requested_inlet_pressure_train2 = get_inlet_pressure(4, date_temporal_1, models)
    requested_inlet_pressure_train2_upgr = get_inlet_pressure(5, date_temporal_2, models)
    requested_inlet_pressure_train3 = get_inlet_pressure(6, date_temporal_1, models)

    requested_outlet_pressure_train1 = get_outlet_pressure(2, date_temporal_1, models)
    requested_outlet_pressure_train1_upgr = get_outlet_pressure(3, date_temporal_2, models)
    requested_outlet_pressure_train2 = get_outlet_pressure(4, date_temporal_1, models)
    requested_outlet_pressure_train2_upgr = get_outlet_pressure(5, date_temporal_2, models)
    requested_outlet_pressure_train3 = get_outlet_pressure(6, date_temporal_1, models)

    # Temporal model 1
    assert requested_inlet_pressure_train1 in [20.0, 50.0]
    assert requested_inlet_pressure_train2 in [30.0, 60.0]
    assert requested_inlet_pressure_train3 in [40.0, 70.0]
    assert requested_outlet_pressure_train1 in [220.0, 250.0]
    assert requested_outlet_pressure_train2 in [230.0, 260.0]
    assert requested_outlet_pressure_train3 in [240.0, 270.0]

    # Temporal model 2
    assert requested_inlet_pressure_train1_upgr == 40
    assert requested_inlet_pressure_train2_upgr == 45
    assert requested_outlet_pressure_train1_upgr == 240
    assert requested_outlet_pressure_train2_upgr == 245


def test_model_timestep_not_in_energy_usage_model(compressor_systems_and_compressor_train_temporal_dto):
    graph = compressor_systems_and_compressor_train_temporal_dto.ecalc_model.get_graph()
    compressor_system = graph.get_node("compressor_system_variable_speed_compressor_trains_multiple_pressures")

    energy_usage_model = compressor_system.energy_usage_model

    variables = compressor_systems_and_compressor_train_temporal_dto.variables
    energy_calculator = EnergyCalculator(graph=graph)
    consumer_results = energy_calculator.evaluate_energy_usage(variables)
    operational_settings_used = consumer_results[
        "compressor_system_variable_speed_compressor_trains_multiple_pressures"
    ].component_result.operational_settings_used

    model_timesteps = [datetime(2018, 1, 1), datetime(2021, 7, 1), datetime(2022, 1, 1)]

    # Ensure that method do not fail if model timesteps do not correspond exactly to dates in temporal model
    get_requested_compressor_pressures(
        energy_usage_model=energy_usage_model,
        pressure_type=CompressorPressureType.INLET_PRESSURE,
        model_timesteps=model_timesteps,
        name="train1",
        operational_settings_used=operational_settings_used,
    )
