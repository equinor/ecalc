"""Golden snapshot baseline for the two-stage solver-path matrix.

The golden snapshot file is a *curated projection* of the **legacy** solver's results — the
single source of truth for the numeric expectations (train and per-stage power, pressures,
speed) and the per-stage chart-area flags that otherwise had to be hand-maintained and
re-baselined whenever legacy behavior changed.

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

from math import isnan
from pathlib import Path

from libecalc.domain.process.compressor.core.results import CompressorTrainResultSingleTimeStep

from ..utils import (
    LEGACY_FAILURE_TO_OUTCOME,
    recirculation_rate_from_stage,
    snapshot_round,
)
from ..utils import (
    load_golden_snapshot as _load_golden_snapshot,
)

GOLDEN_SNAPSHOT_DIR = Path(__file__).parent / "golden_snapshot"
GOLDEN_SNAPSHOT_NAME = "two_stage_matrix.json"
GOLDEN_SNAPSHOT_PATH = GOLDEN_SNAPSHOT_DIR / GOLDEN_SNAPSHOT_NAME


def project_legacy_result(result: CompressorTrainResultSingleTimeStep, shaft_speed: float) -> dict:
    """Project a legacy ``evaluate_given_constraints`` result into the golden snapshot schema.

    Curated to exactly the fields the matrix tests assert — nothing more.
    Per-stage recirculation rates are included so ``cases.py`` can derive control actions.
    """
    speed = result.speed if not isnan(result.speed) else shaft_speed
    lp_result, hp_result = result.stage_results[0], result.stage_results[1]
    return {
        "is_valid": bool(result.is_valid),
        "outcome": LEGACY_FAILURE_TO_OUTCOME[result.failure_status].name,
        "power_mw": snapshot_round(result.power_megawatt),
        "discharge_pressure_bara": snapshot_round(result.discharge_pressure),
        "speed": snapshot_round(speed),
        "lp_chart_area": lp_result.chart_area_flag.name,
        "hp_chart_area": hp_result.chart_area_flag.name,
        "lp_power_mw": snapshot_round(lp_result.power_megawatt),
        "hp_power_mw": snapshot_round(hp_result.power_megawatt),
        "lp_recirculation_rate_sm3_day": recirculation_rate_from_stage(lp_result),
        "hp_recirculation_rate_sm3_day": recirculation_rate_from_stage(hp_result),
    }


def load_golden_snapshot() -> dict[str, dict]:
    """Load the committed two-stage golden snapshot."""
    return _load_golden_snapshot(GOLDEN_SNAPSHOT_PATH)
