"""Capacity queries: the maximum standard feed rate the train can move.

This is the inverse question. An outer 1D search on feed rate wraps the full
``solve`` (the inner evaluation): a rate is feasible iff ``solve(...).success``.
The answer sits on whatever bound bites first — the max-speed curve, the
stonewall, or (only if configured) a power ceiling. The search uses
``binary_search_max`` on the boolean "solve succeeds" with
rate tolerance 1e-4. Zero/vanishing rate is a convention, not a numeric case — the
low end is guarded before any thermodynamic call.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import Enum

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process_concept_draft_v3.solver.constraints import Constraint
from libecalc.process_concept_draft_v3.solver.numerics import DidNotConvergeError, binary_search_max
from libecalc.process_concept_draft_v3.solver.result import (
    OperationInfeasibleFailure,
    RateTooHighFailure,
    SolverResult,
    TargetUnreachableFailure,
)
from libecalc.process_concept_draft_v3.solver.solver import solve
from libecalc.process_concept_draft_v3.system import ProcessSystem

RATE_SEARCH_TOLERANCE = 1e-4
RATE_SEARCH_MAX_ITERATIONS = 40
_RATE_EPSILON = 1e-6
_MAX_BRACKET_DOUBLINGS = 40


class Limiter(Enum):
    MAX_SPEED = "max_speed"
    STONEWALL = "stonewall"
    TARGET_UNREACHABLE = "target_unreachable"
    POWER = "power"
    INFEASIBLE = "infeasible"


@dataclass(frozen=True)
class CapacityResult:
    max_rate_sm3_per_day: float
    limiting: Limiter
    result_at_max: SolverResult | None


def _feed_at_rate(system: ProcessSystem, feed: FluidStream, rate: float) -> FluidStream:
    return system.fluid_service.create_stream_from_standard_rate(
        fluid_model=feed.fluid_model,
        pressure_bara=feed.pressure_bara,
        temperature_kelvin=feed.temperature_kelvin,
        standard_rate_m3_per_day=rate,
    )


def _classify(failure: object | None) -> Limiter:
    if isinstance(failure, RateTooHighFailure):
        return Limiter.STONEWALL
    if isinstance(failure, TargetUnreachableFailure):
        return Limiter.MAX_SPEED
    if isinstance(failure, OperationInfeasibleFailure):
        return Limiter.TARGET_UNREACHABLE
    return Limiter.TARGET_UNREACHABLE


def max_standard_rate(
    system: ProcessSystem,
    constraints: Sequence[Constraint],
    feeds: Mapping[str, FluidStream],
    *,
    feed_name: str = "feed",
    rate_bounds: tuple[float, float] | None = None,
    tolerance: float = RATE_SEARCH_TOLERANCE,
) -> CapacityResult:
    feed = feeds[feed_name]

    def result_at(rate: float) -> SolverResult:
        trial_feed = _feed_at_rate(system, feed, rate)
        return solve(system, constraints, {**feeds, feed_name: trial_feed})

    if rate_bounds is not None:
        lower, upper = rate_bounds
    else:
        lower = 0.0
        upper = feed.standard_rate_sm3_per_day if feed.standard_rate_sm3_per_day > 0.0 else 1.0e6
        doublings = 0
        while result_at(upper).success and doublings < _MAX_BRACKET_DOUBLINGS:
            upper *= 2.0
            doublings += 1

    # Degenerate: even a vanishing rate is infeasible -> capacity 0, the failure diagnoses why.
    probe_rate = max(lower, _RATE_EPSILON)
    low_result = result_at(probe_rate)
    if not low_result.success:
        return CapacityResult(
            0.0, _classify(low_result.failure) if low_result.failure else Limiter.INFEASIBLE, low_result
        )

    def probe(rate: float) -> tuple[bool, bool]:
        return result_at(rate).success, True

    try:
        max_rate = binary_search_max(lower, upper, probe, tolerance=tolerance, max_iter=RATE_SEARCH_MAX_ITERATIONS)
    except DidNotConvergeError:
        return CapacityResult(0.0, Limiter.INFEASIBLE, low_result)

    result_at_max = result_at(max_rate)
    # The bound that bites is diagnosed just above the maximum feasible rate.
    just_above = result_at(max_rate * (1.0 + 1e-3) + _RATE_EPSILON)
    limiting = _classify(just_above.failure) if not just_above.success else Limiter.STONEWALL
    return CapacityResult(max_rate, limiting, result_at_max)
