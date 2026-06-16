"""Shared vocabulary and tolerances for the compressor solver-path matrix tests.

These enums, the ``ExpectedResult`` projection, and the comparison tolerances are
shared by both the single-stage and two-stage solver-path matrix suites, so they
live in this common parent package rather than in either suite.
"""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from math import isnan
from pathlib import Path

import pytest

from libecalc.domain.process.compressor.core.results import CompressorTrainStageResultSingleTimeStep
from libecalc.domain.process.core.results.compressor import CompressorTrainCommonShaftFailureStatus
from libecalc.process.process_solver.configuration import Configuration
from libecalc.process.process_solver.solver import (
    RateTooHighFailure,
    Solution,
    TargetDirection,
    TargetPressureUnreachableFailure,
)
from libecalc.process.process_solver.solver import (
    RateTooLowFailure as SolverRateTooLowFailure,
)

# Comparison tolerances shared by every suite.
POWER_TOLERANCE = 0.1  # MW, absolute
PRESSURE_TOLERANCE = 0.01  # bara, absolute
RECIRCULATION_THRESHOLD = 1.0  # Sm³/day above which a stage counts as recirculating

# Decimals retained in golden snapshots. Kept finer than every test tolerance
# so rounding never shifts a stored value by more than the tests allow.
GOLDEN_SNAPSHOT_ROUND_DECIMALS = 3


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


# ---------------------------------------------------------------------------
# Golden snapshot helpers — shared by both suite-specific golden_snapshot.py
# ---------------------------------------------------------------------------

LEGACY_FAILURE_TO_OUTCOME: dict[CompressorTrainCommonShaftFailureStatus, ExpectedOutcome] = {
    CompressorTrainCommonShaftFailureStatus.NO_FAILURE: ExpectedOutcome.SUCCESS,
    CompressorTrainCommonShaftFailureStatus.TARGET_DISCHARGE_PRESSURE_TOO_HIGH: ExpectedOutcome.PRESSURE_TOO_HIGH,
    CompressorTrainCommonShaftFailureStatus.TARGET_DISCHARGE_PRESSURE_TOO_LOW: ExpectedOutcome.PRESSURE_TOO_LOW,
    CompressorTrainCommonShaftFailureStatus.ABOVE_MAXIMUM_FLOW_RATE: ExpectedOutcome.ABOVE_MAX_FLOW,
    CompressorTrainCommonShaftFailureStatus.BELOW_MINIMUM_FLOW_RATE: ExpectedOutcome.BELOW_MIN_FLOW,
    CompressorTrainCommonShaftFailureStatus.NOT_CALCULATED: ExpectedOutcome.NOT_CALCULATED,
}


def snapshot_round(value: float | None) -> float | None:
    """Round a float for golden snapshots; NaN/None become ``None`` (JSON ``null``)."""
    if value is None or isnan(value):
        return None
    return round(float(value), GOLDEN_SNAPSHOT_ROUND_DECIMALS)


def recirculation_rate_from_stage(stage_result: CompressorTrainStageResultSingleTimeStep | None) -> float | None:
    """ASV recirculation = corrected − uncorrected standard rate; ``None`` if unavailable/NaN."""
    if stage_result is None:
        return None
    corrected = stage_result.standard_rate_asv_corrected_sm3_per_day
    uncorrected = stage_result.standard_rate_sm3_per_day
    if isnan(corrected) or isnan(uncorrected):
        return None
    return snapshot_round(corrected - uncorrected)


def project_matrix(projections: dict[str, dict]) -> str:
    """Serialise a ``{case_id: projection}`` mapping to the canonical golden-snapshot text."""
    return json.dumps(projections, sort_keys=True, indent=2) + "\n"


def load_golden_snapshot(path: Path) -> dict[str, dict]:
    """Load a committed golden snapshot keyed by ``"<region>-<mode>"``.

    Returns an empty dict if the file does not yet exist, so that collection
    succeeds during ``--snapshot-update`` before the file has been written.
    """
    if not path.exists():
        return {}
    with path.open() as file:
        return json.load(file)


# ---------------------------------------------------------------------------
# Shared cases.py helpers
# ---------------------------------------------------------------------------


def pressure_expectation_from_legacy(
    outcome: ExpectedOutcome,
    actual_discharge_bara: float | None,
    target_discharge_bara: float,
) -> PressureExpectation:
    """Derive the pressure assertion intent from the legacy outcome and discharge pressure."""
    if actual_discharge_bara is None:
        return PressureExpectation.NAN
    if outcome is ExpectedOutcome.SUCCESS:
        return PressureExpectation.TARGET
    if actual_discharge_bara < target_discharge_bara:
        return PressureExpectation.BELOW_TARGET
    if outcome is ExpectedOutcome.PRESSURE_TOO_LOW:
        # Min-speed floor: the solver cannot reduce pressure to the (low) target, so it overshoots.
        return PressureExpectation.ABOVE_TARGET
    return PressureExpectation.NOT_ASSERTED


# ---------------------------------------------------------------------------
# Shared process test helpers
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Xfail:
    """A documented process-solver divergence from legacy.

    ``raises`` distinguishes a *crash* (uncaught exception) from a merely
    *wrong-but-structured* outcome. When set, the xfail is strict on that exact
    exception type, so the case xpasses (alerting us) once the solver either stops
    crashing or starts returning the correct structured result.
    """

    reason: str
    raises: type[BaseException] | None = None


def outcome_from_process_solution(
    solution: Solution[Sequence[Configuration] | Configuration],
) -> ExpectedOutcome:
    """Map a process solver Solution to our test-level ExpectedOutcome."""
    if solution.success:
        return ExpectedOutcome.SUCCESS
    if solution.failure is None:
        return ExpectedOutcome.NOT_CALCULATED
    match solution.failure:
        case RateTooHighFailure():
            return ExpectedOutcome.ABOVE_MAX_FLOW
        case SolverRateTooLowFailure():
            return ExpectedOutcome.BELOW_MIN_FLOW
        case TargetPressureUnreachableFailure(direction=TargetDirection.MAX_BELOW_TARGET):
            return ExpectedOutcome.PRESSURE_TOO_HIGH
        case TargetPressureUnreachableFailure(direction=TargetDirection.MIN_ABOVE_TARGET):
            return ExpectedOutcome.PRESSURE_TOO_LOW
        case _:
            return ExpectedOutcome.NOT_CALCULATED


def make_xfail_param(case, xfails: dict[tuple[str, str], Xfail]):
    """Create a pytest.param for a case, applying xfail marks from the xfails dict."""
    xfail = xfails.get((case.region.id, case.mode))
    if xfail is None:
        return pytest.param(case, id=case.id)
    mark = (
        pytest.mark.xfail(reason=xfail.reason, strict=True, raises=xfail.raises)
        if xfail.raises is not None
        else pytest.mark.xfail(reason=xfail.reason, strict=True)
    )
    return pytest.param(case, id=case.id, marks=mark)
