from datetime import datetime

import pytest

from libecalc.common.time_utils import Period, Periods
from libecalc.common.units import Unit
from libecalc.common.utils.rates import TimeSeriesFloat
from libecalc.presentation.json_result.mapper import (
    get_asset_result,
)
from libecalc.presentation.json_result.result.results import CompressorModelResult, EcalcModelResult


@pytest.fixture
def result(compressor_systems_and_compressor_train_temporal) -> EcalcModelResult:
    model = compressor_systems_and_compressor_train_temporal.get_yaml_model()
    model.validate_for_run()
    model.evaluate_energy_usage()
    model.evaluate_emissions()

    return get_asset_result(model.get_graph_result())


def get_inlet_pressure(list_index: int, period: Period, models: list[CompressorModelResult]) -> list[float]:
    return models[list_index].requested_inlet_pressure.for_period(period).values


def get_outlet_pressure(list_index: int, period: Period, models: list[CompressorModelResult]) -> list[float]:
    return models[list_index].requested_outlet_pressure.for_period(period).values


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
        == TimeSeriesFloat(
            periods=Periods([Period(datetime(2018, 1, 1), datetime(2019, 1, 1))]), values=[50.0], unit=Unit.BARA
        )
    )
    assert (
        simplified_variable_speed_compressor_train_known_stages_consumer_temporal_model_first.requested_outlet_pressure
        == TimeSeriesFloat(
            periods=Periods([Period(datetime(2018, 1, 1), datetime(2019, 1, 1))]), values=[250.0], unit=Unit.BARA
        )
    )

    assert (
        simplified_variable_speed_compressor_train_known_stages_consumer_temporal_model_second.requested_inlet_pressure
        == TimeSeriesFloat(
            periods=Periods(
                [
                    Period(datetime(2019, 1, 1), datetime(2020, 1, 1)),
                    Period(datetime(2020, 1, 1), datetime(2021, 1, 1)),
                ]
            ),
            values=[40.0, 40.0],
            unit=Unit.BARA,
        )
    )
    assert (
        simplified_variable_speed_compressor_train_known_stages_consumer_temporal_model_second.requested_outlet_pressure
        == TimeSeriesFloat(
            periods=Periods(
                [
                    Period(datetime(2019, 1, 1), datetime(2020, 1, 1)),
                    Period(datetime(2020, 1, 1), datetime(2021, 1, 1)),
                ]
            ),
            values=[260.0, 260.0],
            unit=Unit.BARA,
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
    period1 = Period(datetime(2018, 1, 1), datetime(2019, 1, 1))
    period2 = Period(datetime(2019, 1, 1), datetime(2021, 1, 1))
    models = result.models

    # Compressor system with temporal model and inlet/outlet pressures per compressor
    requested_inlet_pressure_train1 = get_inlet_pressure(2, period1, models)
    requested_inlet_pressure_train1_upgr = get_inlet_pressure(3, period2, models)
    requested_inlet_pressure_train2 = get_inlet_pressure(4, period1, models)
    requested_inlet_pressure_train2_upgr = get_inlet_pressure(5, period2, models)
    requested_inlet_pressure_train3 = get_inlet_pressure(6, period1, models)

    requested_outlet_pressure_train1 = get_outlet_pressure(2, period1, models)
    requested_outlet_pressure_train1_upgr = get_outlet_pressure(3, period2, models)
    requested_outlet_pressure_train2 = get_outlet_pressure(4, period1, models)
    requested_outlet_pressure_train2_upgr = get_outlet_pressure(5, period2, models)
    requested_outlet_pressure_train3 = get_outlet_pressure(6, period1, models)

    # Temporal model 1
    assert requested_inlet_pressure_train1 == [50.0]
    assert requested_inlet_pressure_train2 == [60.0]
    assert requested_inlet_pressure_train3 == [70.0]
    assert requested_outlet_pressure_train1 == [250.0]
    assert requested_outlet_pressure_train2 == [260.0]
    assert requested_outlet_pressure_train3 == [270.0]

    # Temporal model 2
    assert requested_inlet_pressure_train1_upgr == [40, 40]
    assert requested_inlet_pressure_train2_upgr == [45, 45]
    assert requested_outlet_pressure_train1_upgr == [240, 240]
    assert requested_outlet_pressure_train2_upgr == [245, 245]
