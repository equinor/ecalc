"""Legacy solver path matrix tests — two-stage compressor train.

Tests the legacy CompressorTrainCommonShaft.evaluate_given_constraints() across
all 30 trial cases (6 regions × 5 pressure-control modes) for a two-stage
LP + HP configuration.
"""

from __future__ import annotations

from math import isnan

import pytest

from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl
from libecalc.domain.process.compressor.core.results import CompressorTrainStageResultSingleTimeStep
from libecalc.domain.process.compressor.core.train.train_evaluation_input import CompressorTrainEvaluationInput
from libecalc.domain.process.value_objects.chart.chart import ChartData
from libecalc.domain.process.value_objects.chart.chart_area_flag import ChartAreaFlag

from ..utils import LEGACY_FAILURE_TO_OUTCOME, project_matrix
from .assertions import (
    POWER_TOLERANCE,
    assert_control_behavior,
    assert_pressure_expectation,
    assert_speed_boundary,
    assert_stage_power,
    assert_stage_recirculation,
)
from .cases import TEST_CASES, TwoStageTrialCase
from .golden_snapshot import (
    GOLDEN_SNAPSHOT_DIR,
    GOLDEN_SNAPSHOT_NAME,
    load_golden_snapshot,
    project_legacy_result,
)

_GOLDEN_SNAPSHOT = load_golden_snapshot()


def _evaluate_legacy(case: TwoStageTrialCase, lp_chart_data: ChartData, hp_chart_data: ChartData, train_factory):
    """Run the legacy solver for a single case and return (result, shaft_speed)."""
    train = train_factory(
        lp_chart_data=lp_chart_data,
        hp_chart_data=hp_chart_data,
        pressure_control=FixedSpeedPressureControl(case.mode),
    )
    result = train.evaluate_given_constraints(
        CompressorTrainEvaluationInput(
            rates=[case.region.rate_sm3_day],
            suction_pressure=case.region.suction_pressure_bara,
            discharge_pressure=case.region.discharge_pressure_bara,
        )
    )
    return result, train.shaft.get_speed()


def _recirculation(stage_result: CompressorTrainStageResultSingleTimeStep) -> float:
    """Per-stage recirculation = ASV-corrected − uncorrected standard rate."""
    corrected = stage_result.standard_rate_asv_corrected_sm3_per_day
    uncorrected = stage_result.standard_rate_sm3_per_day
    if isnan(corrected) or isnan(uncorrected):
        return 0.0
    return corrected - uncorrected


# ---------------------------------------------------------------------------
# Oracle snapshot test — the golden snapshot is the single source of truth
# ---------------------------------------------------------------------------


@pytest.mark.snapshot
def test_two_stage_legacy_matches_golden_snapshot(
    snapshot,
    variable_speed_compressor_chart_data,
    hp_compressor_chart_data,
    two_stage_legacy_train_factory,
):
    """The legacy solver (oracle) must reproduce the committed golden snapshot.

    Regenerate the snapshot when legacy behavior changes beyond the projection
    rounding::

        uv run pytest -k test_two_stage_legacy_matches_golden_snapshot --snapshot-update
    """
    snapshot.snapshot_dir = GOLDEN_SNAPSHOT_DIR
    actual = {
        case.id: project_legacy_result(
            *_evaluate_legacy(
                case,
                variable_speed_compressor_chart_data,
                hp_compressor_chart_data,
                two_stage_legacy_train_factory,
            )
        )
        for case in TEST_CASES
    }
    snapshot.assert_match(project_matrix(actual), GOLDEN_SNAPSHOT_NAME)


# ---------------------------------------------------------------------------
# Per-case semantic legacy tests — assert behaviors the golden snapshot alone
# cannot capture (per-stage recirculation selectivity, choke effects)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("case", TEST_CASES, ids=lambda case: case.id)
def test_two_stage_legacy_solver_path(
    case: TwoStageTrialCase,
    variable_speed_compressor_chart_data,
    hp_compressor_chart_data,
    two_stage_legacy_train_factory,
):
    # ── Arrange ──────────────────────────────────────────────────────────
    train = two_stage_legacy_train_factory(
        lp_chart_data=variable_speed_compressor_chart_data,
        hp_chart_data=hp_compressor_chart_data,
        pressure_control=FixedSpeedPressureControl(case.mode),
    )

    # ── Act ──────────────────────────────────────────────────────────────
    result = train.evaluate_given_constraints(
        CompressorTrainEvaluationInput(
            rates=[case.region.rate_sm3_day],
            suction_pressure=case.region.suction_pressure_bara,
            discharge_pressure=case.region.discharge_pressure_bara,
        )
    )
    lp_result = result.stage_results[0]
    hp_result = result.stage_results[1]
    speed = result.speed if not isnan(result.speed) else train.shaft.get_speed()

    # ── Assert: outcome ──────────────────────────────────────────────────
    assert result.is_valid is case.expectation.success
    assert LEGACY_FAILURE_TO_OUTCOME[result.failure_status] is case.expectation.outcome

    # ── Assert: pressure and speed ───────────────────────────────────────
    assert_pressure_expectation(result.discharge_pressure, case)
    assert_speed_boundary(speed, variable_speed_compressor_chart_data, case)

    # ── Assert: power ────────────────────────────────────────────────────
    assert result.power_megawatt == pytest.approx(case.expectation.power_mw, abs=POWER_TOLERANCE)

    # ── Assert: per-stage chart area flags (from golden snapshot) ────────
    snapshot = _GOLDEN_SNAPSHOT.get(f"{case.region.id}-{case.mode}")
    if snapshot is not None:
        assert lp_result.chart_area_flag is ChartAreaFlag[snapshot["lp_chart_area"]]
        assert hp_result.chart_area_flag is ChartAreaFlag[snapshot["hp_chart_area"]]

    # ── Assert: per-stage power ──────────────────────────────────────────
    assert_stage_power(case, (lp_result.power_megawatt, hp_result.power_megawatt))

    # ── Assert: per-stage recirculation ──────────────────────────────────
    assert_stage_recirculation(case, (_recirculation(lp_result), _recirculation(hp_result)))

    # ── Assert: train-level pressure control (choke) ─────────────────────
    assert_control_behavior(
        case,
        suction_pressure_after_upstream_choke_bara=(
            lp_result.inlet_stream.pressure_bara if lp_result.inlet_stream is not None else None
        ),
    )
