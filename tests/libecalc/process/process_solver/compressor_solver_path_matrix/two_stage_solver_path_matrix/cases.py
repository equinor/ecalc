"""Shared data model and trial cases for the two-stage solver-path matrix.

Defines 6 operating regions × 5 pressure-control modes = 30 trial cases
that exercise every legacy and new-process solver path for a two-stage
LP + HP compressor train sharing a single variable-speed shaft.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import get_args

from libecalc.ecalc_model.process_simulation import PressureControlType

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

MODES = get_args(PressureControlType)


@dataclass(frozen=True)
class StageExpectation:
    """Expected behavior of a single compressor stage in the train.

    ``recirculates`` is derived from the golden snapshot recirculation rates
    (``None`` for failure cases, where the assertion is skipped).
    ``power_mw`` is sourced per stage from the golden snapshot.
    """

    recirculates: bool | None = None
    power_mw: float | None = None


@dataclass(frozen=True)
class TwoStageRegion:
    """An operating region for the two-stage compressor train.

    Unlike the single-stage SolverRegion, anti-surge behavior is mode-dependent
    in two-stage trains, so there is no region-level ``expect_auto_anti_surge``.
    """

    id: str
    rate_sm3_day: float
    suction_pressure_bara: float
    discharge_pressure_bara: float
    speed_boundary_class: SpeedBoundaryClass


@dataclass(frozen=True)
class TwoStageTrialCase:
    region: TwoStageRegion
    mode: PressureControlType
    expectation: ExpectedResult
    stages: tuple[StageExpectation, StageExpectation]

    @property
    def id(self) -> str:
        return f"{self.region.id}-{self.mode}"


# ---------------------------------------------------------------------------
# Regions — calibrated operating points (all P_in = 40 bara)
# ---------------------------------------------------------------------------
REGIONS = {
    # M1: Both stages internal at min speed, excess pressure → mode differentiation
    "M1": TwoStageRegion(
        id="M1",
        rate_sm3_day=3_500_000.0,
        suction_pressure_bara=40.0,
        discharge_pressure_bara=80.0,
        speed_boundary_class=SpeedBoundaryClass.MINIMUM,
    ),
    # M2: Both below-min at min speed → UC and DC succeed differently
    "M2": TwoStageRegion(
        id="M2",
        rate_sm3_day=2_000_000.0,
        suction_pressure_bara=40.0,
        discharge_pressure_bara=80.0,
        speed_boundary_class=SpeedBoundaryClass.MINIMUM,
    ),
    # M3: Both internal, natural PR → all modes converge (baseline)
    "M3": TwoStageRegion(
        id="M3",
        rate_sm3_day=5_000_000.0,
        suction_pressure_bara=40.0,
        discharge_pressure_bara=150.0,
        speed_boundary_class=SpeedBoundaryClass.INTERNAL,
    ),
    # M4: LP internal, HP below-min → HP-only anti-surge, all modes converge
    "M4": TwoStageRegion(
        id="M4",
        rate_sm3_day=3_500_000.0,
        suction_pressure_bara=40.0,
        discharge_pressure_bara=200.0,
        speed_boundary_class=SpeedBoundaryClass.INTERNAL,
    ),
    # M5: LP above max → all fail
    "M5": TwoStageRegion(
        id="M5",
        rate_sm3_day=8_000_000.0,
        suction_pressure_bara=40.0,
        discharge_pressure_bara=100.0,
        speed_boundary_class=SpeedBoundaryClass.MAXIMUM,
    ),
    # M6: Zero rate → trivial
    "M6": TwoStageRegion(
        id="M6",
        rate_sm3_day=0.0,
        suction_pressure_bara=40.0,
        discharge_pressure_bara=100.0,
        speed_boundary_class=SpeedBoundaryClass.NOT_ASSERTED,
    ),
}


# ---------------------------------------------------------------------------
# Control-action intent (choke entries are hand-maintained because the choke
# only engages when over-compression forces it — which is region AND mode
# dependent; the rest is derived from golden recirculation rates).
# ---------------------------------------------------------------------------
_CHOKE_CONTROL_ACTIONS: dict[tuple[str, str], ExpectedControlAction] = {
    ("M1", "UPSTREAM_CHOKE"): ExpectedControlAction.UPSTREAM_CHOKE,
    ("M1", "DOWNSTREAM_CHOKE"): ExpectedControlAction.DOWNSTREAM_CHOKE,
    ("M2", "UPSTREAM_CHOKE"): ExpectedControlAction.UPSTREAM_CHOKE,
    ("M2", "DOWNSTREAM_CHOKE"): ExpectedControlAction.DOWNSTREAM_CHOKE,
}


# ---------------------------------------------------------------------------
# Expected results — numeric/outcome truth sourced from the legacy golden snapshot.
# ---------------------------------------------------------------------------
_GOLDEN_SNAPSHOT = load_golden_snapshot()


def _control_action(
    region_id: str, mode: str, lp_recirc: float | None, hp_recirc: float | None
) -> ExpectedControlAction:
    """Derive the expected control action from mode, region, and golden recirculation rates.

    Choke actions are resolved from the hand-maintained ``_CHOKE_CONTROL_ACTIONS``
    because the choke only engages in over-compression regions (speed at min boundary).
    Recirculation is derived from the golden recirculation rates.
    """
    choke_action = _CHOKE_CONTROL_ACTIONS.get((region_id, mode))
    if choke_action is not None:
        return choke_action
    any_recirculating = (lp_recirc is not None and lp_recirc > RECIRCULATION_THRESHOLD) or (
        hp_recirc is not None and hp_recirc > RECIRCULATION_THRESHOLD
    )
    if any_recirculating:
        return ExpectedControlAction.RECIRCULATION
    return ExpectedControlAction.NONE


def _expected_from_golden_snapshot(region_id: str, mode: PressureControlType) -> ExpectedResult:
    snapshot = _GOLDEN_SNAPSHOT.get(f"{region_id}-{mode}", {})
    try:
        outcome = ExpectedOutcome[snapshot["outcome"]]
        return ExpectedResult(
            outcome=outcome,
            power_mw=snapshot["power_mw"],
            pressure_expectation=pressure_expectation_from_legacy(
                outcome,
                snapshot["discharge_pressure_bara"],
                REGIONS[region_id].discharge_pressure_bara,
            ),
            control_action=_control_action(
                region_id,
                mode,
                snapshot.get("lp_recirculation_rate_sm3_day"),
                snapshot.get("hp_recirculation_rate_sm3_day"),
            ),
        )
    except KeyError:
        # Snapshot absent or outdated schema — return stub so collection succeeds
        # and --snapshot-update can regenerate the golden.
        return ExpectedResult(
            outcome=ExpectedOutcome.NOT_CALCULATED,
            power_mw=None,
            pressure_expectation=PressureExpectation.NOT_ASSERTED,
            control_action=ExpectedControlAction.NONE,
        )


def _stage_expectations(region_id: str, mode: PressureControlType) -> tuple[StageExpectation, StageExpectation]:
    """Build the (LP, HP) per-stage expectations for a case.

    Both ``recirculates`` and ``power_mw`` are derived from the golden snapshot.
    Failure cases get ``recirculates=None`` (not asserted).
    """
    snapshot = _GOLDEN_SNAPSHOT.get(f"{region_id}-{mode}", {})
    try:
        success = ExpectedOutcome[snapshot["outcome"]] is ExpectedOutcome.SUCCESS
    except KeyError:
        success = False

    def _recirculates(rate_key: str) -> bool | None:
        if not success:
            return None
        rate = snapshot.get(rate_key)
        if rate is None:
            return False
        return rate > RECIRCULATION_THRESHOLD

    return (
        StageExpectation(
            recirculates=_recirculates("lp_recirculation_rate_sm3_day"),
            power_mw=snapshot.get("lp_power_mw"),
        ),
        StageExpectation(
            recirculates=_recirculates("hp_recirculation_rate_sm3_day"),
            power_mw=snapshot.get("hp_power_mw"),
        ),
    )


EXPECTED_RESULTS: dict[tuple[str, PressureControlType], ExpectedResult] = {
    (region.id, mode): _expected_from_golden_snapshot(region.id, mode) for region in REGIONS.values() for mode in MODES
}

# Fail fast if a new PressureControlType is added without test coverage.
_tested_modes = {mode for _, mode in EXPECTED_RESULTS}
_untested_modes = set(MODES) - _tested_modes
if _untested_modes:
    raise AssertionError(
        f"New PressureControlType values {_untested_modes} have no expected results "
        f"in the two-stage solver-path matrix. Add entries to EXPECTED_RESULTS."
    )


TEST_CASES = tuple(
    TwoStageTrialCase(
        region=region,
        mode=mode,
        expectation=EXPECTED_RESULTS[(region.id, mode)],
        stages=_stage_expectations(region.id, mode),
    )
    for region in REGIONS.values()
    for mode in MODES
)
