"""Pressure-control fallbacks (upstream choke, common ASV) vs the existing solver."""

from __future__ import annotations

import pytest

from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process_concept_draft_v3.params import Param
from libecalc.process_concept_draft_v3.solver import solve

from .conftest import build_legacy_system, build_v3_system, make_constraint, make_variable_speed_chart


def _legacy(service, charts, mode, target, inlet):
    legacy = build_legacy_system(charts, mode, service)
    solution = legacy.solver.find_solution(pressure_constraint=FloatConstraint(target), inlet_stream=inlet)
    speed = solution.get_configuration(legacy.shaft.get_id()).speed
    outlet = None
    choke_dp = legacy.choke.pressure_change if legacy.choke is not None else None
    if solution.success:
        legacy.runner.apply_configurations(solution.configuration)
        try:
            outlet = legacy.runner.run(inlet_stream=inlet)
        except Exception:
            outlet = None
        choke_dp = legacy.choke.pressure_change if legacy.choke is not None else None
    return solution, speed, outlet, choke_dp


def test_upstream_choke_fallback_parity(fluid_service, make_stream):
    charts = [make_variable_speed_chart()]
    inlet = make_stream(500_000.0, 25.0)
    target = 28.0
    legacy_solution, legacy_speed, legacy_outlet, legacy_dp = _legacy(
        fluid_service, charts, "UPSTREAM_CHOKE", target, inlet
    )

    built = build_v3_system("UPSTREAM_CHOKE", charts, fluid_service)
    result = solve(built.system, [make_constraint(built, "UPSTREAM_CHOKE", target)], {"feed": inlet})

    assert result.success == legacy_solution.success
    if result.success:
        assert result.values[Param(built.shaft, "speed")] == pytest.approx(legacy_speed, abs=1e-6)
        dp = result.values[Param(built.choke, "delta_pressure")]
        assert dp > 0.0
        assert dp == pytest.approx(legacy_dp, abs=1e-2)
        assert result.state.out(built.target_unit).pressure_bara == pytest.approx(target, abs=1e-3)


def test_upstream_choke_stonewall_trim(fluid_service, make_stream):
    """A large feed makes upstream choking hit the stonewall; outcome must match legacy."""
    charts = [make_variable_speed_chart()]
    inlet = make_stream(900_000.0, 25.0)
    target = 30.0
    legacy_solution, _, _, _ = _legacy(fluid_service, charts, "UPSTREAM_CHOKE", target, inlet)

    built = build_v3_system("UPSTREAM_CHOKE", charts, fluid_service)
    result = solve(built.system, [make_constraint(built, "UPSTREAM_CHOKE", target)], {"feed": inlet})
    # Same success/failure verdict as the legacy upstream-choke solver (stonewall-bounded).
    assert result.success == legacy_solution.success


def test_common_asv_fallback_parity(fluid_service, make_stream):
    charts = [make_variable_speed_chart()]
    inlet = make_stream(500_000.0, 25.0)
    target = 28.0
    legacy_solution, _, legacy_outlet, _ = _legacy(fluid_service, charts, "COMMON_ASV", target, inlet)

    built = build_v3_system("COMMON_ASV", charts, fluid_service)
    result = solve(built.system, [make_constraint(built, "COMMON_ASV", target)], {"feed": inlet})

    assert result.success == legacy_solution.success
    if result.success:
        assert result.state.out(built.target_unit).pressure_bara == pytest.approx(target, abs=1e-3)
        assert result.state.out(built.target_unit).pressure_bara == pytest.approx(legacy_outlet.pressure_bara, abs=1e-2)
