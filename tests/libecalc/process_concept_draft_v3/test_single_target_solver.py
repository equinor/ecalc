"""Single-target solver scenarios: common-ASV behavior and the single-speed train."""

from __future__ import annotations

import pytest

from libecalc.domain.process.value_objects.chart import ChartCurve
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process_concept_draft_v3.params import Param
from libecalc.process_concept_draft_v3.solver import solve
from libecalc.testing.chart_data_factory import ChartDataFactory

from .conftest import build_legacy_system, build_v3_system, make_constraint, make_variable_speed_chart


def _legacy_speed_outlet(service, charts, mode, target, inlet):
    legacy = build_legacy_system(charts, mode, service)
    solution = legacy.solver.find_solution(pressure_constraint=FloatConstraint(target), inlet_stream=inlet)
    speed = solution.get_configuration(legacy.shaft.get_id()).speed
    legacy.runner.apply_configurations(solution.configuration)
    outlet = legacy.runner.run(inlet_stream=inlet)
    return solution, speed, outlet


def _single_speed_chart(speed: float = 80.0):
    f = speed / 100.0
    curve = ChartCurve(
        speed_rpm=speed,
        rate_actual_m3_hour=[500.0 * f, 1500.0 * f],
        polytropic_head_joule_per_kg=[70_000.0 * f**2, 50_000.0 * f**2],
        efficiency_fraction=[0.75, 0.75],
    )
    return ChartDataFactory.from_curves([curve], control_margin=0.0)


def test_common_asv_speed_reachable_parity(fluid_service, make_stream):
    charts = [make_variable_speed_chart()]
    inlet = make_stream(500_000.0, 25.0)
    target = 35.0
    _, legacy_speed, _ = _legacy_speed_outlet(fluid_service, charts, "COMMON_ASV", target, inlet)

    built = build_v3_system("COMMON_ASV", charts, fluid_service)
    result = solve(built.system, [make_constraint(built, "COMMON_ASV", target)], {"feed": inlet})

    assert result.success
    assert result.values[Param(built.shaft, "speed")] == pytest.approx(legacy_speed, rel=1e-3)
    assert result.state.out(built.target_unit).pressure_bara == pytest.approx(target, abs=1e-3)
    # Speed alone suffices; the loop is not a solver-chosen value.
    assert Param(built.loop, "rate_sm3_per_day") not in result.values


def test_common_asv_recirculation_engages(fluid_service, make_stream):
    charts = [make_variable_speed_chart()]
    inlet = make_stream(500_000.0, 25.0)
    target = 28.0
    legacy_solution, _, legacy_outlet = _legacy_speed_outlet(fluid_service, charts, "COMMON_ASV", target, inlet)

    built = build_v3_system("COMMON_ASV", charts, fluid_service)
    result = solve(built.system, [make_constraint(built, "COMMON_ASV", target)], {"feed": inlet})

    assert result.success == legacy_solution.success
    if result.success:
        loop_rate = result.values[Param(built.loop, "rate_sm3_per_day")]
        assert loop_rate > 0.0
        assert result.state.out(built.target_unit).pressure_bara == pytest.approx(target, abs=1e-3)
        assert result.state.out(built.target_unit).pressure_bara == pytest.approx(legacy_outlet.pressure_bara, abs=1e-2)


def test_single_speed_chart_pins_and_falls_back(fluid_service, make_stream):
    """One curve -> FROM_CHART gives lo==hi: the solver pins immediately and falls back."""
    charts = [_single_speed_chart(80.0)]
    inlet = make_stream(500_000.0, 25.0)
    built = build_v3_system("DOWNSTREAM_CHOKE", charts, fluid_service)
    # Target below what the single-speed train delivers -> downstream choke engages.
    result = solve(built.system, [make_constraint(built, "DOWNSTREAM_CHOKE", 30.0)], {"feed": inlet})
    assert result.success
    assert result.values[Param(built.shaft, "speed")] == pytest.approx(80.0)
    assert result.values[Param(built.choke, "delta_pressure")] > 0.0
    assert result.state.out(built.target_unit).pressure_bara == pytest.approx(30.0, abs=1e-3)
