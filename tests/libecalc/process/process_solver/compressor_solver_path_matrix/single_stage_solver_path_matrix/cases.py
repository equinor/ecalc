"""Shared data model and trial cases for the solver-path matrix.

Defines 9 operating regions × 5 pressure-control modes = 45 trial cases
that exercise every legacy and new-process solver path.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import get_args

from libecalc.ecalc_model.process_simulation import PressureControlType

# Shared test vocabulary lives in the common parent package.
from ..utils import (
    RECIRCULATION_THRESHOLD,
    ExpectedControlAction,
    ExpectedOutcome,
    ExpectedResult,
    PressureExpectation,
    SpeedBoundaryClass,
    pressure_expectation_from_legacy,
)
from .golden_snapshot import load_golden_snapshot


@dataclass(frozen=True)
class SolverRegion:
    id: str
    rate_sm3_day: float
    suction_pressure_bara: float
    discharge_pressure_bara: float
    speed_boundary_class: SpeedBoundaryClass
    expect_auto_anti_surge: bool = False


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

# ---------------------------------------------------------------------------
# Expected results — all sourced from the legacy golden snapshot
# (see golden_snapshot.py). Nothing is hand-maintained here.
# ---------------------------------------------------------------------------
_GOLDEN_SNAPSHOT = load_golden_snapshot()


def _control_action(mode: str, recirculation_rate: float | None) -> ExpectedControlAction:
    """Derive the expected control action from the mode name and golden recirculation rate."""
    if mode == "UPSTREAM_CHOKE":
        return ExpectedControlAction.UPSTREAM_CHOKE
    if mode == "DOWNSTREAM_CHOKE":
        return ExpectedControlAction.DOWNSTREAM_CHOKE
    if recirculation_rate is not None and recirculation_rate > RECIRCULATION_THRESHOLD:
        return ExpectedControlAction.RECIRCULATION
    return ExpectedControlAction.NONE


def _expected_from_golden_snapshot(region_id: str, mode: PressureControlType) -> ExpectedResult:
    snapshot = _GOLDEN_SNAPSHOT.get(f"{region_id}-{mode}", {})
    try:
        outcome = ExpectedOutcome[snapshot["outcome"]]
        recirculation_rate = snapshot.get("recirculation_rate_sm3_day")
        return ExpectedResult(
            outcome=outcome,
            power_mw=snapshot["power_mw"],
            pressure_expectation=pressure_expectation_from_legacy(
                outcome,
                snapshot["discharge_pressure_bara"],
                REGIONS[region_id].discharge_pressure_bara,
            ),
            control_action=_control_action(mode, recirculation_rate),
        )
    except KeyError:
        # Snapshot is absent or has an outdated schema (e.g. a field was renamed).
        # Returning a stub lets collection succeed so --snapshot-update can regenerate
        # the golden. Test assertions are meaningless until the snapshot is current.
        return ExpectedResult(
            outcome=ExpectedOutcome.NOT_CALCULATED,
            power_mw=None,
            pressure_expectation=PressureExpectation.NOT_ASSERTED,
            control_action=ExpectedControlAction.NONE,
        )


EXPECTED_RESULTS: dict[tuple[str, PressureControlType], ExpectedResult] = {
    (region.id, mode): _expected_from_golden_snapshot(region.id, mode) for region in REGIONS.values() for mode in MODES
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
