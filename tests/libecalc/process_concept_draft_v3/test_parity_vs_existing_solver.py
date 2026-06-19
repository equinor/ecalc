"""Single-target solver and pressure-control fallbacks vs the existing solver."""

from __future__ import annotations

import pytest

from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process_concept_draft_v3.params import Param
from libecalc.process_concept_draft_v3.solver import solve

from .conftest import build_legacy_system, build_v3_system, make_constraint, make_variable_speed_chart


def _legacy_solve(service, charts, mode, target_pressure, inlet):
    legacy = build_legacy_system(charts, mode, service)
    solution = legacy.solver.find_solution(pressure_constraint=FloatConstraint(target_pressure), inlet_stream=inlet)
    speed = solution.get_configuration(legacy.shaft.get_id()).speed
    legacy.runner.apply_configurations(solution.configuration)
    outlet = legacy.runner.run(inlet_stream=inlet)
    choke_dp = legacy.choke.pressure_change if legacy.choke is not None else None
    return solution, speed, outlet, choke_dp


# --------------------------------------------------------------------- speed solve parity


def test_speed_solve_parity(fluid_service, make_stream):
    charts = [make_variable_speed_chart()]
    inlet = make_stream(500_000.0, 25.0)
    target = 35.0
    _, legacy_speed, _, _ = _legacy_solve(fluid_service, charts, "DOWNSTREAM_CHOKE", target, inlet)

    built = build_v3_system("DOWNSTREAM_CHOKE", charts, fluid_service)
    constraint = make_constraint(built, "DOWNSTREAM_CHOKE", target)
    result = solve(built.system, [constraint], {"feed": inlet})

    assert result.success
    speed_param = Param(built.shaft, "speed")
    assert result.values[speed_param] == pytest.approx(legacy_speed, rel=1e-3)
    assert result.state.out(built.target_unit).pressure_bara == pytest.approx(target, abs=1e-3)
    assert Param(built.choke, "delta_pressure") not in result.values  # choke not engaged


def test_speed_solve_known_value(fluid_service, make_stream):
    """The proof-02 scenario hits speed ~84.40 (documented parity number)."""
    charts = [make_variable_speed_chart()]
    inlet = make_stream(500_000.0, 25.0)
    built = build_v3_system("DOWNSTREAM_CHOKE", charts, fluid_service)
    constraint = make_constraint(built, "DOWNSTREAM_CHOKE", 35.0)
    result = solve(built.system, [constraint], {"feed": inlet})
    assert result.values[Param(built.shaft, "speed")] == pytest.approx(84.401672, rel=2e-3)


# --------------------------------------------------------------------- downstream choke escalation


def test_downstream_choke_escalation_parity(fluid_service, make_stream):
    charts = [make_variable_speed_chart()]
    inlet = make_stream(500_000.0, 25.0)
    target = 28.0
    _, legacy_speed, _, legacy_dp = _legacy_solve(fluid_service, charts, "DOWNSTREAM_CHOKE", target, inlet)

    built = build_v3_system("DOWNSTREAM_CHOKE", charts, fluid_service)
    constraint = make_constraint(built, "DOWNSTREAM_CHOKE", target)
    result = solve(built.system, [constraint], {"feed": inlet})

    assert result.success
    speed_param = Param(built.shaft, "speed")
    dp_param = Param(built.choke, "delta_pressure")
    assert result.values[speed_param] == pytest.approx(legacy_speed, abs=1e-6)  # pinned at chart min
    assert result.values[dp_param] > 0.0
    assert result.values[dp_param] == pytest.approx(legacy_dp, abs=1e-3)
    assert result.state.out(built.target_unit).pressure_bara == pytest.approx(target, abs=1e-3)


def test_downstream_choke_known_dp(fluid_service, make_stream):
    charts = [make_variable_speed_chart()]
    inlet = make_stream(500_000.0, 25.0)
    built = build_v3_system("DOWNSTREAM_CHOKE", charts, fluid_service)
    constraint = make_constraint(built, "DOWNSTREAM_CHOKE", 28.0)
    result = solve(built.system, [constraint], {"feed": inlet})
    assert result.values[Param(built.shaft, "speed")] == pytest.approx(60.0, abs=1e-6)
    assert result.values[Param(built.choke, "delta_pressure")] == pytest.approx(1.055187, abs=5e-3)
