"""Shared vocabulary and tolerances for the compressor solver-path matrix tests.

These enums, the ``ExpectedResult`` projection, and the comparison tolerances are
shared by both the single-stage and two-stage solver-path matrix suites, so they
live in this common parent package rather than in either suite.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

# Comparison tolerances shared by every suite.
POWER_TOLERANCE = 0.1  # MW, absolute
PRESSURE_TOLERANCE = 0.01  # bara, absolute
RECIRCULATION_THRESHOLD = 1.0  # Sm³/day above which a stage counts as recirculating


class PressureExpectation(StrEnum):
    TARGET = "target"
    ABOVE_TARGET = "above_target"
    BELOW_TARGET = "below_target"
    NOT_ASSERTED = "not_asserted"
    NAN = "nan"


class SpeedBoundaryClass(StrEnum):
    MINIMUM = "minimum"
    MAXIMUM = "maximum"
    INTERNAL = "internal"
    NOT_ASSERTED = "not_asserted"


class ExpectedControlAction(StrEnum):
    NONE = "none"
    DOWNSTREAM_CHOKE = "downstream_choke"
    UPSTREAM_CHOKE = "upstream_choke"
    RECIRCULATION = "recirculation"


class ExpectedOutcome(StrEnum):
    SUCCESS = "success"
    PRESSURE_TOO_HIGH = "pressure_too_high"
    PRESSURE_TOO_LOW = "pressure_too_low"
    ABOVE_MAX_FLOW = "above_max_flow"
    BELOW_MIN_FLOW = "below_min_flow"
    NOT_CALCULATED = "not_calculated"


@dataclass(frozen=True)
class ExpectedResult:
    outcome: ExpectedOutcome
    power_mw: float | None
    pressure_expectation: PressureExpectation
    control_action: ExpectedControlAction = ExpectedControlAction.NONE

    @property
    def success(self) -> bool:
        return self.outcome is ExpectedOutcome.SUCCESS
