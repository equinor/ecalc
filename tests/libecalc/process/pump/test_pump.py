from typing import NamedTuple

import pytest

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.common.units import UnitConstants
from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.domain.process.pump.pump import PumpModel
from libecalc.process.chart.chart import ChartCurve
from libecalc.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.process.pump.exceptions import NonPositivePressureException
from libecalc.process.pump.liquid_stream import LiquidStream
from libecalc.process.pump.pump import Pump, PumpFailureStatus
from libecalc.testing.pump_test_data import DENSITY_KG_PER_M3

# With the density of the tests, 1 bar of pressure rise is 100 J/kg of head. The single-speed chart is the
# 2000 rpm curve of the variable-speed chart: 90, 85, 80, 70 and 60 bar at 200, 400, 600, 800 and 1000 m3/h.
# The 3000 rpm curve is 175, 170, 160, 150 and 130 bar at 300, 600, 800, 1000 and 1200 m3/h.
SUCTION_PRESSURE = 10.0
SINGLE = "single_speed_chart"
VARIABLE = "variable_speed_chart"


class OperatingPoint(NamedTuple):
    """A rate and a requested outlet pressure, and what the pump does with them."""

    chart_name: str
    rate: float
    requested_outlet_pressure: float
    speed: float
    discharge_pressure: float
    minimum_flow_rate: float | None = None
    recirculation_rate: float = 0.0
    choke_pressure_drop: float = 0.0
    pressure_shortfall: float = 0.0
    failure_status: PumpFailureStatus = PumpFailureStatus.NO_FAILURE


OPERATING_POINTS = {
    # Inside the chart the pump runs at the required head.
    "inside the chart, between the speed curves": OperatingPoint(
        VARIABLE, 600.0, 135.0, speed=2500.0, discharge_pressure=135.0
    ),
    "inside the chart, at the minimum head": OperatingPoint(
        VARIABLE, 600.0, 90.0, speed=2000.0, discharge_pressure=90.0
    ),
    "inside the chart, at the maximum head": OperatingPoint(
        VARIABLE, 600.0, 180.0, speed=3000.0, discharge_pressure=180.0
    ),
    # In the choke region the required head is below the chart's minimum head at the operating rate.
    "choke region, single speed": OperatingPoint(
        SINGLE, 600.0, 60.0, speed=2000.0, discharge_pressure=90.0, choke_pressure_drop=30.0
    ),
    "choke region, at the chart's maximum rate": OperatingPoint(
        SINGLE, 1000.0, 60.0, speed=2000.0, discharge_pressure=70.0, choke_pressure_drop=10.0
    ),
    "choke region, variable speed at the minimum speed": OperatingPoint(
        VARIABLE, 600.0, 50.0, speed=2000.0, discharge_pressure=90.0, choke_pressure_drop=40.0
    ),
    # Above the maximum head the pump runs at the chart's maximum head at the operating rate.
    "above the maximum head, single speed": OperatingPoint(
        SINGLE,
        600.0,
        100.0,
        speed=2000.0,
        discharge_pressure=90.0,
        pressure_shortfall=10.0,
        failure_status=PumpFailureStatus.ABOVE_MAXIMUM_HEAD_AT_RATE,
    ),
    "above the maximum head, variable speed": OperatingPoint(
        VARIABLE,
        600.0,
        200.0,
        speed=3000.0,
        discharge_pressure=180.0,
        pressure_shortfall=20.0,
        failure_status=PumpFailureStatus.ABOVE_MAXIMUM_HEAD_AT_RATE,
    ),
    # Above the maximum rate the rate is kept, and the head is that of the chart's maximum rate.
    "above the maximum rate": OperatingPoint(
        SINGLE,
        1200.0,
        60.0,
        speed=2000.0,
        discharge_pressure=70.0,
        choke_pressure_drop=10.0,
        failure_status=PumpFailureStatus.ABOVE_MAXIMUM_PUMP_RATE,
    ),
    "above the maximum rate and the maximum head": OperatingPoint(
        SINGLE,
        1200.0,
        100.0,
        speed=2000.0,
        discharge_pressure=70.0,
        pressure_shortfall=30.0,
        failure_status=PumpFailureStatus.ABOVE_MAXIMUM_PUMP_RATE_AND_MAXIMUM_HEAD_AT_RATE,
    ),
    # The pump recirculates up to the largest of the chart's minimum rate, the minimum flow and the chart's
    # minimum-flow line at the required head.
    "recirculation up to the chart's minimum rate": OperatingPoint(
        SINGLE, 100.0, 60.0, speed=2000.0, discharge_pressure=100.0, recirculation_rate=100.0, choke_pressure_drop=40.0
    ),
    "recirculation up to the minimum flow": OperatingPoint(
        SINGLE,
        250.0,
        60.0,
        minimum_flow_rate=300.0,
        speed=2000.0,
        discharge_pressure=97.5,
        recirculation_rate=50.0,
        choke_pressure_drop=37.5,
    ),
    # The minimum-flow line goes from 200 m3/h at 90 bar to 300 m3/h at 175 bar, so it is at 250 m3/h for the
    # required head of 132.5 bar. The speed is read between the curves at 250 m3/h, where the head is 88.75 bar at
    # 2000 rpm, and 175 bar at 3000 rpm since that curve starts at 300 m3/h.
    "recirculation up to the chart's minimum-flow line": OperatingPoint(
        VARIABLE, 220.0, 142.5, speed=2507.246377, discharge_pressure=142.5, recirculation_rate=30.0
    ),
}


def _inlet_stream(
    rate_m3_per_hour: float, pressure_bara: float = SUCTION_PRESSURE, density_kg_per_m3: float = DENSITY_KG_PER_M3
) -> LiquidStream:
    return LiquidStream.from_volumetric_rate(
        volumetric_rate_m3_per_day=rate_m3_per_hour * UnitConstants.HOURS_PER_DAY,
        pressure_bara=pressure_bara,
        density_kg_per_m3=density_kg_per_m3,
    )


@pytest.mark.parametrize("point", OPERATING_POINTS.values(), ids=OPERATING_POINTS.keys())
def test_operating_point(request, point):
    pump = Pump(request.getfixturevalue(point.chart_name), minimum_flow_rate_m3_per_hour=point.minimum_flow_rate)

    result = pump.evaluate(_inlet_stream(point.rate), requested_outlet_pressure_bara=point.requested_outlet_pressure)

    assert result.recirculation_rate_m3_per_hour == pytest.approx(point.recirculation_rate)
    assert result.operational_volumetric_rate_m3_per_hour == pytest.approx(point.rate + point.recirculation_rate)
    assert result.speed_rpm == pytest.approx(point.speed)
    assert result.operational_discharge_pressure_bara == pytest.approx(point.discharge_pressure)
    assert result.choke_pressure_drop_bara == pytest.approx(point.choke_pressure_drop)
    assert result.pressure_shortfall_bara == pytest.approx(point.pressure_shortfall)
    assert result.failure_status is point.failure_status


@pytest.mark.parametrize(
    "minimum_flow_rate, rate, requested_outlet_pressure, efficiency, specific_shaft_work_joule_per_kg, shaft_power_mw",
    [
        # The efficiency is 0.5 at 200 m3/h and 0.7 at 400 m3/h, and the head is 87.5 bar at 300 m3/h.
        pytest.param(300.0, 250.0, 60.0, 0.6, 8750.0 / 0.6, 1.215278, id="recirculating: 300 m3/h at 87.5 bar"),
        pytest.param(None, 600.0, 100.0, 0.8, 10000.0, 5.0 / 3.0, id="above the maximum head: 600 m3/h at 80 bar"),
    ],
)
def test_shaft_power_is_for_the_operating_rate_and_the_operational_head(
    single_speed_chart,
    minimum_flow_rate,
    rate,
    requested_outlet_pressure,
    efficiency,
    specific_shaft_work_joule_per_kg,
    shaft_power_mw,
):
    pump = Pump(single_speed_chart, minimum_flow_rate_m3_per_hour=minimum_flow_rate)

    result = pump.evaluate(_inlet_stream(rate), requested_outlet_pressure)

    assert result.efficiency == pytest.approx(efficiency)
    assert result.specific_shaft_work_joule_per_kg == pytest.approx(specific_shaft_work_joule_per_kg)
    assert result.shaft_power_mw == pytest.approx(shaft_power_mw)


def test_pump_with_no_rate_is_not_running(single_speed_chart):
    result = Pump(single_speed_chart).evaluate(_inlet_stream(0.0), requested_outlet_pressure_bara=60.0)

    assert result.is_valid
    assert result.speed_rpm is None
    assert result.efficiency is None
    assert result.specific_shaft_work_joule_per_kg is None
    assert result.shaft_power_mw == 0.0
    assert result.operational_volumetric_rate_m3_per_hour == 0.0
    assert result.operational_discharge_pressure_bara == SUCTION_PRESSURE


def test_result_carries_process_unit_id(single_speed_chart):
    process_unit_id = ProcessUnitId(ecalc_id_generator())
    pump = Pump(single_speed_chart, process_unit_id=process_unit_id)

    running = pump.evaluate(_inlet_stream(600.0), requested_outlet_pressure_bara=60.0)
    not_running = pump.evaluate(_inlet_stream(0.0), requested_outlet_pressure_bara=60.0)

    assert running.process_unit_id == process_unit_id
    assert not_running.process_unit_id == process_unit_id


def test_evaluate_rejects_non_positive_outlet_pressure(single_speed_chart):
    with pytest.raises(NonPositivePressureException):
        Pump(single_speed_chart).evaluate(_inlet_stream(600.0), requested_outlet_pressure_bara=0.0)


def test_rejects_zero_efficiency_pump_chart(chart_data_factory):
    chart = chart_data_factory.from_curves(
        curves=[
            ChartCurve(
                speed_rpm=2000.0,
                rate_actual_m3_hour=[200.0, 400.0],
                polytropic_head_joule_per_kg=[9000.0, 8500.0],
                efficiency_fraction=[0.0, 0.0],
            )
        ]
    )

    with pytest.raises(EcalcValidationException, match="Pump efficiency must be greater than zero"):
        Pump(chart)


def test_propagating_a_stream_with_a_rate_requires_a_speed(single_speed_chart):
    pump = Pump(single_speed_chart)

    assert pump.propagate_stream(_inlet_stream(0.0)) == _inlet_stream(0.0)
    with pytest.raises(ValueError, match="Speed not set"):
        pump.propagate_stream(_inlet_stream(600.0))


LEGACY_DENSITY = 1021.0
LEGACY_CHART_MINIMUM_RATE = 277.0
LEGACY_MINIMUM_SPEED_CURVE = ChartCurve(
    speed_rpm=2650.0,
    rate_actual_m3_hour=[277.0, 524.0, 666.0, 832.0, 927.0],
    polytropic_head_joule_per_kg=[10415.277, 9845.316, 9254.754, 8308.089, 7605.693],
    efficiency_fraction=[0.4759, 0.6426, 0.6871, 0.7052, 0.6908],
)
LEGACY_MAXIMUM_SPEED_CURVE = ChartCurve(
    speed_rpm=3425.0,
    rate_actual_m3_hour=[336.0, 577.0, 708.0, 842.0, 1028.0],
    polytropic_head_joule_per_kg=[17449.047, 16860.447, 16335.612, 15576.318, 14328.486],
    efficiency_fraction=[0.4717, 0.6203, 0.6683, 0.6996, 0.7193],
)


@pytest.mark.parametrize(
    "curves, rate, requested_outlet_pressure",
    [
        pytest.param([LEGACY_MINIMUM_SPEED_CURVE], 600.0, 100.0, id="single speed"),
        pytest.param([LEGACY_MINIMUM_SPEED_CURVE], 150.0, 100.0, id="single speed, recirculating"),
        pytest.param([LEGACY_MINIMUM_SPEED_CURVE], 600.0, 50.0, id="single speed, choke region"),
        pytest.param([LEGACY_MINIMUM_SPEED_CURVE, LEGACY_MAXIMUM_SPEED_CURVE], 600.0, 100.0, id="variable speed"),
        pytest.param(
            [LEGACY_MINIMUM_SPEED_CURVE, LEGACY_MAXIMUM_SPEED_CURVE],
            150.0,
            100.0,
            id="variable speed, recirculating",
        ),
        pytest.param(
            [LEGACY_MINIMUM_SPEED_CURVE, LEGACY_MAXIMUM_SPEED_CURVE], 600.0, 50.0, id="variable speed, choke region"
        ),
        pytest.param(
            [LEGACY_MINIMUM_SPEED_CURVE, LEGACY_MAXIMUM_SPEED_CURVE],
            1200.0,
            100.0,
            id="variable speed, above the maximum rate",
        ),
    ],
)
def test_power_matches_the_legacy_pump(chart_data_factory, curves, rate, requested_outlet_pressure):
    """Where the required head is not above the chart's maximum head, the power is that of the legacy pump."""
    chart_data = chart_data_factory.from_curves(curves=curves)
    legacy_power, _, _ = PumpModel(pump_chart=chart_data).simulate(
        rate=rate * UnitConstants.HOURS_PER_DAY,
        suction_pressure=5.0,
        discharge_pressure=requested_outlet_pressure,
        fluid_density=LEGACY_DENSITY,
    )

    result = Pump(chart_data, minimum_flow_rate_m3_per_hour=LEGACY_CHART_MINIMUM_RATE).evaluate(
        _inlet_stream(rate, pressure_bara=5.0, density_kg_per_m3=LEGACY_DENSITY),
        requested_outlet_pressure_bara=requested_outlet_pressure,
    )

    assert result.shaft_power_mw == pytest.approx(legacy_power)
