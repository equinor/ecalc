"""Failure taxonomy, SolverResult shape, and construction validity (proof-06 cases)."""

from __future__ import annotations

import pytest

from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.process_solver.solver import (
    TargetPressureUnreachableFailure as LegacyTargetUnreachableFailure,
)
from libecalc.process_concept_draft_v3.params import Param
from libecalc.process_concept_draft_v3.solver import (
    FROM_CAPACITY,
    FROM_CHART,
    Constraint,
    Probe,
    RateTooHighFailure,
    Target,
    TargetDirection,
    TargetUnreachableFailure,
    solve,
)

from .conftest import build_legacy_system, build_v3_system, make_constraint, make_variable_speed_chart


def test_case_a_stonewall_rate_too_high(fluid_service, make_stream):
    charts = [make_variable_speed_chart()]
    huge_feed = make_stream(3_000_000.0, 25.0)
    built = build_v3_system("DOWNSTREAM_CHOKE", charts, fluid_service)
    result = solve(built.system, [make_constraint(built, "DOWNSTREAM_CHOKE", 35.0)], {"feed": huge_feed})
    assert not result.success
    assert isinstance(result.failure, RateTooHighFailure)
    assert result.failure.unit is built.stages[0]


def test_case_b_target_above_max_speed_max_below(fluid_service, make_stream):
    charts = [make_variable_speed_chart()]
    feed = make_stream(500_000.0, 25.0)
    legacy = build_legacy_system(charts, "DOWNSTREAM_CHOKE", fluid_service)
    legacy_solution = legacy.solver.find_solution(FloatConstraint(200.0), inlet_stream=feed)
    assert isinstance(legacy_solution.failure, LegacyTargetUnreachableFailure)

    built = build_v3_system("DOWNSTREAM_CHOKE", charts, fluid_service)
    result = solve(built.system, [make_constraint(built, "DOWNSTREAM_CHOKE", 200.0)], {"feed": feed})
    assert not result.success
    assert isinstance(result.failure, TargetUnreachableFailure)
    assert result.failure.direction is TargetDirection.MAX_BELOW_TARGET
    assert result.failure.achievable == pytest.approx(legacy_solution.failure.achievable_pressure_bara, abs=1e-3)


def test_case_b_achievable_known_value(fluid_service, make_stream):
    charts = [make_variable_speed_chart()]
    feed = make_stream(500_000.0, 25.0)
    built = build_v3_system("DOWNSTREAM_CHOKE", charts, fluid_service)
    result = solve(built.system, [make_constraint(built, "DOWNSTREAM_CHOKE", 200.0)], {"feed": feed})
    assert result.failure.achievable == pytest.approx(40.619, abs=5e-2)


def test_case_c_min_above_no_fallback(fluid_service, make_stream):
    charts = [make_variable_speed_chart()]
    feed = make_stream(500_000.0, 25.0)
    built = build_v3_system("DOWNSTREAM_CHOKE", charts, fluid_service)
    # No fallback: target below min-speed delivery must fail MIN_ABOVE.
    constraint = Constraint(
        vary=Param(built.shaft, "speed"),
        target=Target(probe=Probe.outlet_pressure(built.target_unit), value=28.0),
        bounds=FROM_CHART,
        fallback=None,
    )
    result = solve(built.system, [constraint], {"feed": feed})
    assert not result.success
    assert isinstance(result.failure, TargetUnreachableFailure)
    assert result.failure.direction is TargetDirection.MIN_ABOVE_TARGET


def test_result_carries_state_and_auto_values(fluid_service, make_stream):
    charts = [make_variable_speed_chart()]
    feed = make_stream(500_000.0, 25.0)
    built = build_v3_system("DOWNSTREAM_CHOKE", charts, fluid_service)
    result = solve(built.system, [make_constraint(built, "DOWNSTREAM_CHOKE", 35.0)], {"feed": feed})
    assert result.success
    assert result.state is not None and result.state.feasible
    assert isinstance(result.values, dict)
    assert isinstance(result.auto_values, dict)


# --------------------------------------------------------------- construction validity


def test_from_chart_on_non_shaft_raises(fluid_service):
    built = build_v3_system("DOWNSTREAM_CHOKE", [make_variable_speed_chart()], fluid_service)
    target = Target(probe=Probe.outlet_pressure(built.target_unit), value=35.0)
    with pytest.raises(ValueError, match="FROM_CHART"):
        Constraint(vary=Param(built.choke, "delta_pressure"), target=target, bounds=FROM_CHART)


def test_from_capacity_on_non_recirculation_raises(fluid_service):
    built = build_v3_system("DOWNSTREAM_CHOKE", [make_variable_speed_chart()], fluid_service)
    target = Target(probe=Probe.outlet_pressure(built.target_unit), value=35.0)
    with pytest.raises(ValueError, match="FROM_CAPACITY"):
        Constraint(vary=Param(built.shaft, "speed"), target=target, bounds=FROM_CAPACITY)


def test_empty_constraints_raises(fluid_service, make_stream):
    built = build_v3_system("DOWNSTREAM_CHOKE", [make_variable_speed_chart()], fluid_service)
    with pytest.raises(ValueError):
        solve(built.system, [], {"feed": make_stream(500_000.0, 25.0)})
