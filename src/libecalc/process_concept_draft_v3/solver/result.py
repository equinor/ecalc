"""Typed failures and the solver result.

The failure taxonomy is a user-facing diagnosis produced by the bracket-endpoint
probes of the solver. Identities are object handles (the offending ``Unit`` /
the ``Probe``), not UUIDs. ``SolverResult`` keeps the controller's choices in a
separate ``auto_values`` map from the solver's own ``values``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum

from libecalc.process_concept_draft_v3.params import Param
from libecalc.process_concept_draft_v3.system import CapacityViolation, State, ViolationKind
from libecalc.process_concept_draft_v3.units import Unit


class SolverFailure:
    """Typed cause for an unsuccessful solve; branch with isinstance/match."""


@dataclass(frozen=True)
class RateTooHighFailure(SolverFailure):
    unit: Unit
    actual_rate_m3_per_hour: float | None = None
    maximum_rate_m3_per_hour: float | None = None


@dataclass(frozen=True)
class RateTooLowFailure(SolverFailure):
    unit: Unit
    actual_rate_m3_per_hour: float | None = None
    minimum_rate_m3_per_hour: float | None = None


@dataclass(frozen=True)
class OperationInfeasibleFailure(SolverFailure):
    """Non-rate capacity violation (e.g. choking to negative pressure)."""

    unit: Unit
    reason: str = ""


class TargetDirection(Enum):
    """Which side of the target the achievable boundary lies on."""

    MAX_BELOW_TARGET = "max_below_target"
    MIN_ABOVE_TARGET = "min_above_target"


@dataclass(frozen=True)
class TargetUnreachableFailure(SolverFailure):
    probe: object  # a Probe (solver/constraints.py); kept loosely typed to avoid a cycle
    achievable: float
    target_value: float
    direction: TargetDirection


def failure_from_violation(violation: CapacityViolation) -> SolverFailure:
    match violation.kind:
        case ViolationKind.RATE_TOO_LOW:
            return RateTooLowFailure(
                unit=violation.unit,
                actual_rate_m3_per_hour=violation.actual,
                minimum_rate_m3_per_hour=violation.bound,
            )
        case ViolationKind.RATE_TOO_HIGH:
            return RateTooHighFailure(
                unit=violation.unit,
                actual_rate_m3_per_hour=violation.actual,
                maximum_rate_m3_per_hour=violation.bound,
            )
        case _:
            return OperationInfeasibleFailure(unit=violation.unit, reason=violation.reason)


@dataclass(frozen=True)
class SolverResult:
    success: bool
    values: Mapping[Param, float]
    auto_values: Mapping[Param, float]
    state: State | None = None
    failure: SolverFailure | None = None
