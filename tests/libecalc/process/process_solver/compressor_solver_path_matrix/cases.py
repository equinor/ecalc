"""Shared data model and trial cases for the solver-path matrix.

Defines 9 operating regions × 5 pressure-control modes = 45 trial cases
that exercise every legacy and new-process solver path.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import get_args

from libecalc.ecalc_model.process_simulation import PressureControlType


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


@dataclass(frozen=True)
class SolverRegion:
    id: str
    rate_sm3_day: float
    suction_pressure_bara: float
    discharge_pressure_bara: float
    speed_boundary_class: SpeedBoundaryClass
    expect_auto_anti_surge: bool = False


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
    power_mw: float
    pressure_expectation: PressureExpectation
    control_action: ExpectedControlAction = ExpectedControlAction.NONE

    @property
    def success(self) -> bool:
        return self.outcome is ExpectedOutcome.SUCCESS


@dataclass(frozen=True)
class TrialCase:
    region: SolverRegion
    mode: PressureControlType
    expectation: ExpectedResult

    @property
    def id(self) -> str:
        return f"{self.region.id}-{self.mode}"


MODES = get_args(PressureControlType)

REGIONS = {
    "R1": SolverRegion(
        id="R1",
        rate_sm3_day=5_000_000.0,
        suction_pressure_bara=40.0,
        discharge_pressure_bara=100.0,
        speed_boundary_class=SpeedBoundaryClass.INTERNAL,
    ),
    "R2": SolverRegion(
        id="R2",
        rate_sm3_day=2_000_000.0,
        suction_pressure_bara=40.0,
        discharge_pressure_bara=90.0,
        speed_boundary_class=SpeedBoundaryClass.INTERNAL,
        expect_auto_anti_surge=True,
    ),
    "R3": SolverRegion(
        id="R3",
        rate_sm3_day=500_000.0,
        suction_pressure_bara=40.0,
        discharge_pressure_bara=60.0,
        speed_boundary_class=SpeedBoundaryClass.MINIMUM,
        expect_auto_anti_surge=True,
    ),
    "R4": SolverRegion(
        id="R4",
        rate_sm3_day=5_000_000.0,
        suction_pressure_bara=40.0,
        discharge_pressure_bara=200.0,
        speed_boundary_class=SpeedBoundaryClass.MAXIMUM,
    ),
    "R5": SolverRegion(
        id="R5",
        rate_sm3_day=15_000_000.0,
        suction_pressure_bara=40.0,
        discharge_pressure_bara=50.0,
        speed_boundary_class=SpeedBoundaryClass.MAXIMUM,
    ),
    "R6": SolverRegion(
        id="R6",
        rate_sm3_day=5_000_000.0,
        suction_pressure_bara=40.0,
        discharge_pressure_bara=108.0,
        speed_boundary_class=SpeedBoundaryClass.INTERNAL,
    ),
    "R7": SolverRegion(
        id="R7",
        rate_sm3_day=3_500_000.0,
        suction_pressure_bara=40.0,
        discharge_pressure_bara=62.0,
        speed_boundary_class=SpeedBoundaryClass.MINIMUM,
    ),
    "R8": SolverRegion(
        id="R8",
        rate_sm3_day=0.0,
        suction_pressure_bara=40.0,
        discharge_pressure_bara=100.0,
        speed_boundary_class=SpeedBoundaryClass.NOT_ASSERTED,
    ),
    "R9": SolverRegion(
        id="R9",
        rate_sm3_day=4_000_000.0,
        suction_pressure_bara=40.0,
        discharge_pressure_bara=45.0,
        speed_boundary_class=SpeedBoundaryClass.MINIMUM,
    ),
}


def _ok(
    power_mw: float,
    control: ExpectedControlAction = ExpectedControlAction.NONE,
    pressure: PressureExpectation = PressureExpectation.TARGET,
) -> ExpectedResult:
    return ExpectedResult(
        outcome=ExpectedOutcome.SUCCESS, power_mw=power_mw, pressure_expectation=pressure, control_action=control
    )


def _fail(
    outcome: ExpectedOutcome,
    power_mw: float,
    pressure: PressureExpectation = PressureExpectation.NOT_ASSERTED,
    control: ExpectedControlAction = ExpectedControlAction.NONE,
) -> ExpectedResult:
    return ExpectedResult(outcome=outcome, power_mw=power_mw, pressure_expectation=pressure, control_action=control)


EXPECTED_RESULTS: dict[tuple[str, PressureControlType], ExpectedResult] = {
    # R1 — nominal internal point, all modes succeed
    ("R1", "UPSTREAM_CHOKE"): _ok(8.231),
    ("R1", "DOWNSTREAM_CHOKE"): _ok(8.231),
    ("R1", "INDIVIDUAL_ASV_RATE"): _ok(8.231),
    ("R1", "INDIVIDUAL_ASV_PRESSURE"): _ok(8.231),
    ("R1", "COMMON_ASV"): _ok(8.231),
    # R2 — below minimum flow, auto anti-surge brings it back
    ("R2", "UPSTREAM_CHOKE"): _ok(5.283),
    ("R2", "DOWNSTREAM_CHOKE"): _ok(5.283),
    ("R2", "INDIVIDUAL_ASV_RATE"): _ok(5.283),
    ("R2", "INDIVIDUAL_ASV_PRESSURE"): _ok(5.283),
    ("R2", "COMMON_ASV"): _ok(5.283),
    # R3 — minimum speed, pressure control active
    ("R3", "DOWNSTREAM_CHOKE"): _ok(2.492, ExpectedControlAction.DOWNSTREAM_CHOKE),
    ("R3", "UPSTREAM_CHOKE"): _ok(2.227, ExpectedControlAction.UPSTREAM_CHOKE),
    ("R3", "INDIVIDUAL_ASV_RATE"): _ok(2.967, ExpectedControlAction.RECIRCULATION),
    ("R3", "INDIVIDUAL_ASV_PRESSURE"): _ok(2.967, ExpectedControlAction.RECIRCULATION),
    ("R3", "COMMON_ASV"): _ok(2.967, ExpectedControlAction.RECIRCULATION),
    # R4 — target pressure unreachable (too high)
    ("R4", "UPSTREAM_CHOKE"): _fail(ExpectedOutcome.PRESSURE_TOO_HIGH, 9.288, PressureExpectation.BELOW_TARGET),
    ("R4", "DOWNSTREAM_CHOKE"): _fail(ExpectedOutcome.PRESSURE_TOO_HIGH, 9.288, PressureExpectation.BELOW_TARGET),
    ("R4", "INDIVIDUAL_ASV_RATE"): _fail(ExpectedOutcome.PRESSURE_TOO_HIGH, 9.288, PressureExpectation.BELOW_TARGET),
    ("R4", "INDIVIDUAL_ASV_PRESSURE"): _fail(
        ExpectedOutcome.PRESSURE_TOO_HIGH, 9.288, PressureExpectation.BELOW_TARGET
    ),
    ("R4", "COMMON_ASV"): _fail(ExpectedOutcome.PRESSURE_TOO_HIGH, 9.288, PressureExpectation.BELOW_TARGET),
    # R5 — above maximum flow rate
    ("R5", "UPSTREAM_CHOKE"): _fail(ExpectedOutcome.ABOVE_MAX_FLOW, 22.47),
    ("R5", "DOWNSTREAM_CHOKE"): _fail(ExpectedOutcome.ABOVE_MAX_FLOW, 22.47),
    ("R5", "INDIVIDUAL_ASV_RATE"): _fail(ExpectedOutcome.ABOVE_MAX_FLOW, 22.47),
    ("R5", "INDIVIDUAL_ASV_PRESSURE"): _fail(ExpectedOutcome.ABOVE_MAX_FLOW, 22.47),
    ("R5", "COMMON_ASV"): _fail(ExpectedOutcome.ABOVE_MAX_FLOW, 22.47),
    # R6 — near max speed, all modes succeed
    ("R6", "UPSTREAM_CHOKE"): _ok(9.053),
    ("R6", "DOWNSTREAM_CHOKE"): _ok(9.053),
    ("R6", "INDIVIDUAL_ASV_RATE"): _ok(9.053),
    ("R6", "INDIVIDUAL_ASV_PRESSURE"): _ok(9.053),
    ("R6", "COMMON_ASV"): _ok(9.053),
    # R7 — minimum speed, pressure control active
    ("R7", "DOWNSTREAM_CHOKE"): _ok(2.824, ExpectedControlAction.DOWNSTREAM_CHOKE),
    ("R7", "UPSTREAM_CHOKE"): _ok(2.767, ExpectedControlAction.UPSTREAM_CHOKE),
    ("R7", "INDIVIDUAL_ASV_RATE"): _ok(2.945, ExpectedControlAction.RECIRCULATION),
    ("R7", "INDIVIDUAL_ASV_PRESSURE"): _ok(2.945, ExpectedControlAction.RECIRCULATION),
    ("R7", "COMMON_ASV"): _ok(2.945, ExpectedControlAction.RECIRCULATION),
    # R8 — zero rate (not calculated)
    ("R8", "UPSTREAM_CHOKE"): _ok(0.0, pressure=PressureExpectation.NAN),
    ("R8", "DOWNSTREAM_CHOKE"): _ok(0.0, pressure=PressureExpectation.NAN),
    ("R8", "INDIVIDUAL_ASV_RATE"): _ok(0.0, pressure=PressureExpectation.NAN),
    ("R8", "INDIVIDUAL_ASV_PRESSURE"): _ok(0.0, pressure=PressureExpectation.NAN),
    ("R8", "COMMON_ASV"): _ok(0.0, pressure=PressureExpectation.NAN),
    # R9 — edge case: high rate + low target pressure
    ("R9", "DOWNSTREAM_CHOKE"): _ok(2.950, ExpectedControlAction.DOWNSTREAM_CHOKE),
    ("R9", "UPSTREAM_CHOKE"): _fail(
        ExpectedOutcome.ABOVE_MAX_FLOW, 2.697, control=ExpectedControlAction.UPSTREAM_CHOKE
    ),
    ("R9", "INDIVIDUAL_ASV_RATE"): _fail(
        ExpectedOutcome.PRESSURE_TOO_LOW, 2.964, control=ExpectedControlAction.RECIRCULATION
    ),
    ("R9", "INDIVIDUAL_ASV_PRESSURE"): _fail(
        ExpectedOutcome.PRESSURE_TOO_LOW, 2.964, control=ExpectedControlAction.RECIRCULATION
    ),
    ("R9", "COMMON_ASV"): _fail(ExpectedOutcome.PRESSURE_TOO_LOW, 2.970),
}

# Fail fast if a new PressureControlType is added without test coverage.
_tested_modes = {mode for _, mode in EXPECTED_RESULTS}
_untested_modes = set(MODES) - _tested_modes
if _untested_modes:
    raise AssertionError(
        f"New PressureControlType values {_untested_modes} have no expected results in the solver-path matrix. "
        f"Add entries to EXPECTED_RESULTS for each new mode."
    )


TEST_CASES = tuple(
    TrialCase(region=region, mode=mode, expectation=EXPECTED_RESULTS[(region.id, mode)])
    for region in REGIONS.values()
    for mode in MODES
)
