"""Golden snapshot baseline for the single-stage solver-path matrix.

The golden snapshot file is a *curated projection* of the **legacy** solver's results — the
single source of truth for the numeric expectations (power, pressures, speed) and the chart-area
flag that otherwise had to be hand-maintained and re-baselined whenever legacy behavior changed.

Design:
    * Legacy is the oracle. The golden snapshot file is generated from it.
    * The projection is small and curated (only the fields the tests assert) — never a
      full result-object dump.
    * The file holds *correct* legacy values only. It knows nothing about the process
      solver's known divergences (those live in the process test's xfail table).
    * The file is owned by ``pytest-snapshot``: the oracle test regenerates it with
      ``--snapshot-update`` and otherwise asserts the freshly projected legacy result matches it.
      ``cases.py`` loads the same file as plain JSON and derives the per-case expectations that
      ``test_process_solver.py`` asserts against. The projection rounding is kept finer than those
      tolerances, so the stored values are, for the tests' purposes, as good as exact.
"""

from __future__ import annotations

import json
from math import isnan
from pathlib import Path

from libecalc.domain.process.core.results.compressor import CompressorTrainCommonShaftFailureStatus

# Reuse shared vocabulary from the common parent package.
from ..utils import ExpectedOutcome

GOLDEN_SNAPSHOT_DIR = Path(__file__).parent / "golden_snapshot"
GOLDEN_SNAPSHOT_NAME = "single_stage_matrix.json"
GOLDEN_SNAPSHOT_PATH = GOLDEN_SNAPSHOT_DIR / GOLDEN_SNAPSHOT_NAME

# Decimals retained in the golden snapshot. Kept finer than every test tolerance
# so rounding never shifts a stored value by more than the tests allow
# — i.e. rounding can't cause false pass/fail.
_ROUND_DECIMALS = 3

LEGACY_FAILURE_TO_OUTCOME: dict[CompressorTrainCommonShaftFailureStatus, ExpectedOutcome] = {
    CompressorTrainCommonShaftFailureStatus.NO_FAILURE: ExpectedOutcome.SUCCESS,
    CompressorTrainCommonShaftFailureStatus.TARGET_DISCHARGE_PRESSURE_TOO_HIGH: ExpectedOutcome.PRESSURE_TOO_HIGH,
    CompressorTrainCommonShaftFailureStatus.TARGET_DISCHARGE_PRESSURE_TOO_LOW: ExpectedOutcome.PRESSURE_TOO_LOW,
    CompressorTrainCommonShaftFailureStatus.ABOVE_MAXIMUM_FLOW_RATE: ExpectedOutcome.ABOVE_MAX_FLOW,
    CompressorTrainCommonShaftFailureStatus.BELOW_MINIMUM_FLOW_RATE: ExpectedOutcome.BELOW_MIN_FLOW,
    CompressorTrainCommonShaftFailureStatus.NOT_CALCULATED: ExpectedOutcome.NOT_CALCULATED,
}


def _round(value: float | None) -> float | None:
    """Round a float for the golden snapshot; NaN/None become ``null``."""
    if value is None or isnan(value):
        return None
    return round(float(value), _ROUND_DECIMALS)


def _recirculation_rate(stage_result) -> float | None:
    """ASV recirculation = corrected − uncorrected standard rate; ``None`` if unavailable/NaN."""
    if stage_result is None:
        return None
    corrected = stage_result.standard_rate_asv_corrected_sm3_per_day
    uncorrected = stage_result.standard_rate_sm3_per_day
    if isnan(corrected) or isnan(uncorrected):
        return None
    return _round(corrected - uncorrected)


def project_legacy_result(result) -> dict:
    """Project a legacy ``evaluate_given_constraints`` result into the golden snapshot schema.

    Only raw legacy outputs are stored — the matrix tests derive their interpretation
    (pressure expectation, control action) from these in ``cases.py``.
    """
    chart_area = result.chart_area_status
    stage_result = result.stage_results[0] if result.stage_results else None
    return {
        "is_valid": bool(result.is_valid),
        "outcome": LEGACY_FAILURE_TO_OUTCOME[result.failure_status].name,
        "power_mw": _round(result.power_megawatt),
        "discharge_pressure_bara": _round(result.discharge_pressure),
        "speed": _round(result.speed),
        "chart_area": chart_area.name if chart_area is not None else None,
        "recirculation_rate_sm3_day": _recirculation_rate(stage_result),
    }


def project_matrix(projections: dict[str, dict]) -> str:
    """Serialise a ``{case_id: projection}`` mapping to the canonical golden-snapshot text."""
    return json.dumps(projections, sort_keys=True, indent=2) + "\n"


def load_golden_snapshot() -> dict[str, dict]:
    """Load the committed golden snapshot keyed by ``"<region>-<mode>"``.

    Returns an empty dict if the file does not yet exist, so that collection
    succeeds during ``--snapshot-update`` before the file has been written.
    """
    if not GOLDEN_SNAPSHOT_PATH.exists():
        return {}
    with GOLDEN_SNAPSHOT_PATH.open() as file:
        return json.load(file)
