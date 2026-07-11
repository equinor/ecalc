"""Balanced individual-ASV modes (coupled parameters) vs the existing solver."""

from __future__ import annotations

import pytest

from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process_concept_draft_v3.params import Param
from libecalc.process_concept_draft_v3.solver import solve

from .conftest import build_legacy_system, build_v3_system, make_constraint, make_variable_speed_chart


def _legacy(service, charts, mode, target, inlet):
    legacy = build_legacy_system(charts, mode, service)
    solution = legacy.solver.find_solution(pressure_constraint=FloatConstraint(target), inlet_stream=inlet)
    outlet = None
    if solution.success:
        legacy.runner.apply_configurations(solution.configuration)
        try:
            outlet = legacy.runner.run(inlet_stream=inlet)
        except Exception:
            outlet = None
    return solution, outlet


@pytest.mark.parametrize("mode", ["INDIVIDUAL_ASV_RATE", "INDIVIDUAL_ASV_PRESSURE"])
@pytest.mark.parametrize("target", [40.0, 50.0])
def test_balanced_modes_vs_legacy_train(fluid_service, make_stream, mode, target):
    charts = [make_variable_speed_chart(), make_variable_speed_chart()]
    inlet = make_stream(500_000.0, 25.0)
    legacy_solution, legacy_outlet = _legacy(fluid_service, charts, mode, target, inlet)

    built = build_v3_system(mode, charts, fluid_service)
    result = solve(built.system, [make_constraint(built, mode, target)], {"feed": inlet})

    assert result.success == legacy_solution.success
    if result.success and legacy_outlet is not None:
        assert result.state.out(built.target_unit).pressure_bara == pytest.approx(target, abs=1e-2)
        assert result.state.out(built.target_unit).pressure_bara == pytest.approx(legacy_outlet.pressure_bara, abs=5e-2)


@pytest.mark.parametrize("mode", ["INDIVIDUAL_ASV_RATE", "INDIVIDUAL_ASV_PRESSURE"])
def test_balanced_mode_engages_stage_recirculations(fluid_service, make_stream, mode):
    chart = make_variable_speed_chart()
    inlet = make_stream(500_000.0, 25.0)
    # Discover the recirculation floor (max-recirc pressure) so the target lands in-band.
    probe = build_v3_system(mode, [chart, make_variable_speed_chart()], fluid_service)
    floor_result = solve(probe.system, [make_constraint(probe, mode, 1.0)], {"feed": inlet})
    floor = floor_result.failure.achievable
    target = floor + 0.05

    built = build_v3_system(mode, [chart, make_variable_speed_chart()], fluid_service)
    result = solve(built.system, [make_constraint(built, mode, target)], {"feed": inlet})
    assert result.success
    rates = [
        result.values.get(
            Param(stage, "recirculation_rate"), result.auto_values.get(Param(stage, "recirculation_rate"), 0.0)
        )
        for stage in built.stages
    ]
    assert all(rate >= 0.0 for rate in rates)
    assert result.state.out(built.target_unit).pressure_bara == pytest.approx(target, abs=1e-2)


def test_single_stage_modes_coincide(fluid_service, make_stream):
    """For one stage all recycle modes coincide (the under-determination collapses)."""
    chart = make_variable_speed_chart()
    inlet = make_stream(500_000.0, 25.0)

    # Discover the achievable floor (max recirculation) for a single stage.
    probe = build_v3_system("COMMON_ASV", [chart], fluid_service)
    floor_result = solve(probe.system, [make_constraint(probe, "COMMON_ASV", 1.0)], {"feed": inlet})
    floor = floor_result.failure.achievable
    target = floor + 0.05  # in-band: recirculation fallback engages and is reachable

    recircs = {}
    for mode in ["COMMON_ASV", "INDIVIDUAL_ASV_RATE", "INDIVIDUAL_ASV_PRESSURE"]:
        built = build_v3_system(mode, [chart], fluid_service)
        result = solve(built.system, [make_constraint(built, mode, target)], {"feed": inlet})
        assert result.success
        if mode == "COMMON_ASV":
            recircs[mode] = result.values[Param(built.loop, "rate_sm3_per_day")]
        else:
            recircs[mode] = result.values[Param(built.stages[0], "recirculation_rate")]
        assert result.state.out(built.target_unit).pressure_bara == pytest.approx(target, abs=1e-3)

    values = list(recircs.values())
    # All within the capacity-search tolerance band of each other.
    assert max(values) - min(values) < max(0.02 * max(values), 50.0)
