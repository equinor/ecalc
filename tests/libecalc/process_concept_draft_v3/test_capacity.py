"""Capacity (max standard rate) vs the legacy FeasibilitySolver."""

from __future__ import annotations

import pytest

from libecalc.process.process_solver.feasibility_solver import FeasibilitySolver
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process_concept_draft_v3.solver import Limiter, max_standard_rate, solve

from .conftest import build_legacy_system, build_v3_system, make_constraint, make_variable_speed_chart


def _legacy_capacity(service, charts, mode, target, feed):
    legacy = build_legacy_system(charts, mode, service)
    feasibility = FeasibilitySolver(pipeline_section_solver=legacy.solver)
    excess = feasibility.get_excess_rate(feed, FloatConstraint(target))
    return feed.standard_rate_sm3_per_day - excess


@pytest.mark.parametrize("mode", ["DOWNSTREAM_CHOKE", "COMMON_ASV"])
def test_max_rate_parity_with_feasibility_solver(fluid_service, make_stream, mode):
    charts = [make_variable_speed_chart()]
    target = 35.0
    # Feed well ABOVE capacity so the legacy solver actually trims to the true maximum.
    feed = make_stream(5_000_000.0, 25.0)
    legacy_capacity = _legacy_capacity(fluid_service, charts, mode, target, feed)

    built = build_v3_system(mode, charts, fluid_service)
    constraint = make_constraint(built, mode, target)
    result = max_standard_rate(built.system, [constraint], {"feed": feed})

    # v3's more robust speed bracket can certify a few near-boundary rates the legacy
    # FeasibilitySolver (20-iteration cap) rejects, so v3 capacity is >= legacy within a
    # few percent.
    assert result.max_rate_sm3_per_day == pytest.approx(legacy_capacity, rel=3e-2)
    assert result.max_rate_sm3_per_day >= legacy_capacity - 1.0


def test_feasible_feed_is_movable(fluid_service, make_stream):
    """A feed inside capacity solves successfully (capacity is at least the feed rate)."""
    charts = [make_variable_speed_chart()]
    feed = make_stream(500_000.0, 25.0)
    built = build_v3_system("DOWNSTREAM_CHOKE", charts, fluid_service)
    constraint = make_constraint(built, "DOWNSTREAM_CHOKE", 35.0)
    assert solve(built.system, [constraint], {"feed": feed}).success
    result = max_standard_rate(built.system, [constraint], {"feed": feed})
    assert result.max_rate_sm3_per_day >= feed.standard_rate_sm3_per_day


def test_stonewall_limited_capacity(fluid_service, make_stream):
    charts = [make_variable_speed_chart()]
    feed = make_stream(5_000_000.0, 25.0)
    built = build_v3_system("DOWNSTREAM_CHOKE", charts, fluid_service)
    constraint = make_constraint(built, "DOWNSTREAM_CHOKE", 35.0)
    result = max_standard_rate(built.system, [constraint], {"feed": feed})
    assert result.max_rate_sm3_per_day > 0.0
    assert result.limiting in {Limiter.STONEWALL, Limiter.MAX_SPEED}
    assert result.result_at_max is not None and result.result_at_max.success


def test_zero_capacity_when_target_unreachable_at_any_rate(fluid_service, make_stream):
    """An impossible target (above max-speed capability) yields capacity 0."""
    charts = [make_variable_speed_chart()]
    feed = make_stream(500_000.0, 25.0)
    built = build_v3_system("DOWNSTREAM_CHOKE", charts, fluid_service)
    constraint = make_constraint(built, "DOWNSTREAM_CHOKE", 500.0)  # unreachable
    result = max_standard_rate(built.system, [constraint], {"feed": feed})
    assert result.max_rate_sm3_per_day == 0.0
