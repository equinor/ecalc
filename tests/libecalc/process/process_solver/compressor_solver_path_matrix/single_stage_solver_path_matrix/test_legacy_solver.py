"""Legacy solver oracle test for the single-stage solver-path matrix.

Verifies that the legacy CompressorTrainCommonShaft.evaluate_given_constraints()
reproduces the committed golden snapshot across all 45 trial cases
(9 regions × 5 pressure-control modes).
"""

from __future__ import annotations

import pytest

from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl
from libecalc.domain.process.compressor.core.train.train_evaluation_input import CompressorTrainEvaluationInput

from ..utils import project_matrix
from .cases import TEST_CASES, TrialCase
from .golden_snapshot import (
    GOLDEN_SNAPSHOT_DIR,
    GOLDEN_SNAPSHOT_NAME,
    project_legacy_result,
)


def _evaluate_legacy(case: TrialCase, chart_data, legacy_train_factory):
    """Run the legacy solver for a single case and return its result."""
    train = legacy_train_factory(
        chart_data=chart_data,
        pressure_control=FixedSpeedPressureControl(case.mode),
    )
    return train.evaluate_given_constraints(
        CompressorTrainEvaluationInput(
            rates=[case.region.rate_sm3_day],
            suction_pressure=case.region.suction_pressure_bara,
            discharge_pressure=case.region.discharge_pressure_bara,
        )
    )


@pytest.mark.snapshot
def test_legacy_matches_golden_snapshot(
    snapshot,
    variable_speed_compressor_chart_data,
    legacy_train_factory,
):
    """The legacy solver (oracle) must reproduce the committed golden snapshot.

    The golden snapshot is the single source of legacy numeric/outcome truth that ``cases.py``
    and the per-case tests read. Regenerate it when legacy behavior changes beyond the projection
    rounding::

        uv run pytest -k test_legacy_matches_golden_snapshot --snapshot-update
    """
    snapshot.snapshot_dir = GOLDEN_SNAPSHOT_DIR
    actual = {
        case.id: project_legacy_result(
            _evaluate_legacy(case, variable_speed_compressor_chart_data, legacy_train_factory)
        )
        for case in TEST_CASES
    }
    snapshot.assert_match(project_matrix(actual), GOLDEN_SNAPSHOT_NAME)
