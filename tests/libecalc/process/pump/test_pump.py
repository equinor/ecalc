import pytest

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.domain.process.pump.pump import PumpModel
from libecalc.domain.process.value_objects.chart import Chart
from libecalc.domain.process.value_objects.chart.chart import ChartCurve
from libecalc.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.process.pump.exceptions import NonPositivePressureException
from libecalc.process.pump.liquid_stream import LiquidStream
from libecalc.process.pump.pump import Pump, PumpFailureStatus

DENSITY = 1021.0
CHART_MIN_FLOW = 277.0  # m3/h, minimum rate of both test charts


def _single_speed_chart(chart_data_factory):
    return chart_data_factory.from_curves(
        curves=[
            ChartCurve(
                speed_rpm=1,
                rate_actual_m3_hour=[277.0, 524.0, 666.0, 832.0, 927.0],
                polytropic_head_joule_per_kg=[10415.277, 9845.316, 9254.754, 8308.089, 7605.693],
                efficiency_fraction=[0.4759, 0.6426, 0.6871, 0.7052, 0.6908],
            )
        ]
    )


def _variable_speed_chart(chart_data_factory):
    data = [
        (
            2650,
            [277, 524, 666, 832, 927],
            [1061.7, 1003.6, 943.4, 846.9, 775.3],
            [0.4759, 0.6426, 0.6871, 0.7052, 0.6908],
        ),
        (
            3425,
            [336, 577, 708, 842, 1028],
            [1778.7, 1718.7, 1665.2, 1587.8, 1460.6],
            [0.4717, 0.6203, 0.6683, 0.6996, 0.7193],
        ),
    ]
    curves = [
        ChartCurve(
            speed_rpm=float(s),
            rate_actual_m3_hour=[float(x) for x in r],
            polytropic_head_joule_per_kg=[h * 9.81 for h in hm],
            efficiency_fraction=e,
        )
        for s, r, hm, e in data
    ]
    return chart_data_factory.from_curves(curves=curves)


@pytest.fixture
def single_speed_chart(chart_data_factory):
    return _single_speed_chart(chart_data_factory)


@pytest.fixture
def variable_speed_chart(chart_data_factory):
    return _variable_speed_chart(chart_data_factory)


def _inlet(rate_m3_per_hour, suction_pressure, density=DENSITY):
    return LiquidStream.from_volumetric_rate(
        volumetric_rate_m3_per_day=rate_m3_per_hour * 24.0,
        pressure_bara=suction_pressure,
        density_kg_per_m3=density,
    )


@pytest.mark.parametrize(
    "chart_name, rate_m3h, suction, discharge",
    [
        ("single_speed_chart", 600, 5.0, 100.0),  # normal
        ("single_speed_chart", 150, 5.0, 100.0),  # below min flow -> recirculation
        ("single_speed_chart", 600, 5.0, 50.0),  # required head below curve -> over-delivery / choke
        ("variable_speed_chart", 600, 5.0, 100.0),  # normal
        ("variable_speed_chart", 150, 5.0, 100.0),  # below min flow -> recirculation
        ("variable_speed_chart", 600, 5.0, 50.0),  # required head below curve -> over-delivery / choke
        ("variable_speed_chart", 1200, 5.0, 100.0),  # rate above max, but head still within the max-speed curve
    ],
)
def test_power_matches_legacy(request, chart_name, rate_m3h, suction, discharge):
    """Parity with the legacy pump for every point the pump can actually serve."""
    chart_data = request.getfixturevalue(chart_name)
    pump = Pump(chart_data, minimum_flow_rate_m3_per_hour=CHART_MIN_FLOW)
    legacy_power, _, _ = PumpModel(pump_chart=chart_data).simulate(
        rate=rate_m3h * 24.0, suction_pressure=suction, discharge_pressure=discharge, fluid_density=DENSITY
    )
    result = pump.evaluate(_inlet(rate_m3h, suction), discharge_pressure_bara=discharge)
    assert result.shaft_power_mw == pytest.approx(legacy_power)


@pytest.mark.parametrize(
    "chart_name, rate_m3h, discharge, legacy_power",
    [
        ("single_speed_chart", 600, 250.0, 8.580233942705052),
        ("single_speed_chart", 1200, 100.0, 4.490451881262998),
        ("variable_speed_chart", 600, 250.0, 6.904430715116509),
    ],
)
def test_power_diverges_from_legacy_above_chart_capacity(request, chart_name, rate_m3h, discharge, legacy_power):
    """Above the envelope we deliberately bound the head, where legacy did not.

    Legacy computes power at the requested (unachievable) head; we compute it at the pump's actual
    capacity. These periods are flagged is_valid = False either way.
    """
    chart_data = request.getfixturevalue(chart_name)
    pump = Pump(chart_data, minimum_flow_rate_m3_per_hour=CHART_MIN_FLOW)
    result = pump.evaluate(_inlet(rate_m3h, 5.0), discharge_pressure_bara=discharge)

    assert not result.is_valid
    assert result.shaft_power_mw < legacy_power  # bounded below the legacy value


def test_recirculation_up_to_minimum_flow(single_speed_chart):
    pump = Pump(single_speed_chart, minimum_flow_rate_m3_per_hour=600.0)
    result = pump.evaluate(_inlet(400, suction_pressure=5.0), discharge_pressure_bara=90.0)
    assert result.operational_volumetric_rate_m3_per_hour == pytest.approx(600.0)
    assert result.recirculation_rate_m3_per_hour == pytest.approx(200.0)
    assert result.efficiency is not None
    assert result.specific_shaft_work_joule_per_kg is not None
    operating_mass_rate_kg_per_h = result.operational_volumetric_rate_m3_per_hour * DENSITY
    specific_shaft_work_joule_per_kg = result.specific_shaft_work_joule_per_kg
    assert specific_shaft_work_joule_per_kg is not None
    assert result.shaft_power_mw == pytest.approx(
        operating_mass_rate_kg_per_h * specific_shaft_work_joule_per_kg / 3600.0 / 1_000_000.0
    )


def test_over_delivery_exposes_operating_vs_required_and_choke(single_speed_chart):
    # Single-speed head is pinned to the curve, so a low target over-delivers and needs a choke.
    pump = Pump(single_speed_chart, minimum_flow_rate_m3_per_hour=CHART_MIN_FLOW)
    result = pump.evaluate(_inlet(600, suction_pressure=5.0), discharge_pressure_bara=50.0)
    assert result.operational_head_joule_per_kg > result.required_head_joule_per_kg
    assert result.operational_discharge_pressure_bara > result.required_discharge_pressure_bara
    assert result.choke_pressure_drop_bara == pytest.approx(
        result.operational_discharge_pressure_bara - result.required_discharge_pressure_bara
    )
    assert result.is_valid


def test_head_is_bounded_by_chart_maximum(single_speed_chart):
    # A duty above the chart's capacity is bounded to the maximum-speed curve, not left unbounded.
    pump = Pump(single_speed_chart, minimum_flow_rate_m3_per_hour=CHART_MIN_FLOW)
    result = pump.evaluate(_inlet(666, suction_pressure=5.0), discharge_pressure_bara=250.0)

    max_head = float(Chart(single_speed_chart).maximum_head_as_function_of_rate(666.0))
    assert result.operational_head_joule_per_kg == pytest.approx(max_head)
    assert result.required_head_joule_per_kg > result.operational_head_joule_per_kg
    assert result.operational_discharge_pressure_bara < result.required_discharge_pressure_bara
    assert result.pressure_shortfall_bara > 0
    assert result.choke_pressure_drop_bara == 0.0


@pytest.mark.parametrize(
    "discharge, expect_choke, expect_shortfall",
    [
        (50.0, True, False),  # below the min-speed curve -> over-delivery, choked
        (250.0, False, True),  # above the max-speed curve -> shortfall
    ],
)
def test_choke_and_shortfall_are_mutually_exclusive(variable_speed_chart, discharge, expect_choke, expect_shortfall):
    pump = Pump(variable_speed_chart, minimum_flow_rate_m3_per_hour=CHART_MIN_FLOW)
    result = pump.evaluate(_inlet(666, suction_pressure=5.0), discharge_pressure_bara=discharge)

    assert not (result.choke_pressure_drop_bara > 0 and result.pressure_shortfall_bara > 0)
    assert (result.choke_pressure_drop_bara > 0) is expect_choke
    assert (result.pressure_shortfall_bara > 0) is expect_shortfall


def test_efficiency_above_capacity_is_taken_at_the_operating_rate(single_speed_chart):
    # The clamped point lies on the curve, so efficiency is exact, not projected from a different rate.
    pump = Pump(single_speed_chart, minimum_flow_rate_m3_per_hour=CHART_MIN_FLOW)
    result = pump.evaluate(_inlet(666, suction_pressure=5.0), discharge_pressure_bara=250.0)
    chart = Chart(single_speed_chart)
    expected = float(chart.curves[0].efficiency_as_function_of_rate(666.0))
    assert result.efficiency == pytest.approx(expected, rel=1e-3)


def test_variable_speed_in_band_sits_on_target_with_interpolated_speed(variable_speed_chart):
    pump = Pump(variable_speed_chart, minimum_flow_rate_m3_per_hour=CHART_MIN_FLOW)
    result = pump.evaluate(_inlet(600, suction_pressure=5.0), discharge_pressure_bara=140.0)
    assert result.operational_discharge_pressure_bara == pytest.approx(140.0)
    assert result.choke_pressure_drop_bara == pytest.approx(0.0)
    assert result.speed_rpm is not None
    assert 2650.0 < result.speed_rpm < 3425.0
    assert result.efficiency is not None
    specific_shaft_work_joule_per_kg = result.specific_shaft_work_joule_per_kg
    assert specific_shaft_work_joule_per_kg is not None
    assert specific_shaft_work_joule_per_kg == pytest.approx(result.operational_head_joule_per_kg / result.efficiency)
    assert result.shaft_power_mw == pytest.approx(
        result.inlet_stream.mass_rate_kg_per_h * specific_shaft_work_joule_per_kg / 3600.0 / 1_000_000.0
    )


@pytest.mark.parametrize(
    "chart_name, rate_m3h, discharge, expected_status",
    [
        ("single_speed_chart", 600, 250.0, PumpFailureStatus.ABOVE_MAXIMUM_HEAD_AT_RATE),
        ("variable_speed_chart", 1200, 100.0, PumpFailureStatus.ABOVE_MAXIMUM_PUMP_RATE),
        ("single_speed_chart", 1200, 100.0, PumpFailureStatus.ABOVE_MAXIMUM_PUMP_RATE_AND_MAXIMUM_HEAD_AT_RATE),
    ],
)
def test_feasibility_status(request, chart_name, rate_m3h, discharge, expected_status):
    chart_data = request.getfixturevalue(chart_name)
    pump = Pump(chart_data, minimum_flow_rate_m3_per_hour=CHART_MIN_FLOW)
    result = pump.evaluate(_inlet(rate_m3h, suction_pressure=5.0), discharge_pressure_bara=discharge)
    assert result.failure_status == expected_status
    assert not result.is_valid


def test_not_running_when_rate_is_zero(single_speed_chart):
    pump = Pump(single_speed_chart, minimum_flow_rate_m3_per_hour=CHART_MIN_FLOW)
    result = pump.evaluate(_inlet(0.0, suction_pressure=5.0), discharge_pressure_bara=100.0)
    assert result.shaft_power_mw == 0.0
    assert result.efficiency is None
    assert result.specific_shaft_work_joule_per_kg is None
    assert result.speed_rpm is None
    assert result.is_valid


def test_evaluate_rejects_non_positive_discharge_pressure(single_speed_chart):
    pump = Pump(single_speed_chart, minimum_flow_rate_m3_per_hour=CHART_MIN_FLOW)

    with pytest.raises(NonPositivePressureException):
        pump.evaluate(_inlet(600, suction_pressure=5.0), discharge_pressure_bara=0.0)


def test_rejects_zero_efficiency_pump_chart(chart_data_factory):
    chart = chart_data_factory.from_curves(
        curves=[
            ChartCurve(
                speed_rpm=1,
                rate_actual_m3_hour=[100.0, 200.0],
                polytropic_head_joule_per_kg=[10000.0, 9000.0],
                efficiency_fraction=[0.0, 0.0],
            )
        ]
    )

    with pytest.raises(EcalcValidationException, match="Pump efficiency must be greater than zero"):
        Pump(chart, minimum_flow_rate_m3_per_hour=100.0)


def test_result_carries_process_unit_id(single_speed_chart):
    provided_id = ProcessUnitId(ecalc_id_generator())
    pump = Pump(single_speed_chart, CHART_MIN_FLOW, process_unit_id=provided_id)
    running = pump.evaluate(_inlet(600, suction_pressure=5.0), discharge_pressure_bara=100.0)
    not_running = pump.evaluate(_inlet(0.0, suction_pressure=5.0), discharge_pressure_bara=100.0)
    assert running.process_unit_id == provided_id
    assert not_running.process_unit_id == provided_id
