"""Legacy solver path matrix tests.

Tests the legacy CompressorTrainCommonShaft.evaluate_given_constraints() across
all 45 trial cases (9 regions × 5 pressure-control modes).
"""

from __future__ import annotations

from math import isnan

import pytest

from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl
from libecalc.domain.process.compressor.core.train.train_evaluation_input import CompressorTrainEvaluationInput
from libecalc.domain.process.core.results.compressor import CompressorTrainCommonShaftFailureStatus
from libecalc.domain.process.value_objects.chart.chart_area_flag import ChartAreaFlag

from .assertions import (
    POWER_TOLERANCE,
    assert_control_behavior,
    assert_pressure_expectation,
    assert_speed_boundary,
)
from .cases import TEST_CASES, ExpectedOutcome, TrialCase

_LEGACY_TO_OUTCOME: dict[CompressorTrainCommonShaftFailureStatus, ExpectedOutcome] = {
    CompressorTrainCommonShaftFailureStatus.NO_FAILURE: ExpectedOutcome.SUCCESS,
    CompressorTrainCommonShaftFailureStatus.TARGET_DISCHARGE_PRESSURE_TOO_HIGH: ExpectedOutcome.PRESSURE_TOO_HIGH,
    CompressorTrainCommonShaftFailureStatus.TARGET_DISCHARGE_PRESSURE_TOO_LOW: ExpectedOutcome.PRESSURE_TOO_LOW,
    CompressorTrainCommonShaftFailureStatus.ABOVE_MAXIMUM_FLOW_RATE: ExpectedOutcome.ABOVE_MAX_FLOW,
    CompressorTrainCommonShaftFailureStatus.BELOW_MINIMUM_FLOW_RATE: ExpectedOutcome.BELOW_MIN_FLOW,
    CompressorTrainCommonShaftFailureStatus.NOT_CALCULATED: ExpectedOutcome.NOT_CALCULATED,
}

# Per-region chart area flag. R4 is intentionally absent (assertion skipped).
LEGACY_CHART_AREAS: dict[tuple[str, str], ChartAreaFlag] = {
    # R1 — internal point for all modes
    ("R1", "UPSTREAM_CHOKE"): ChartAreaFlag.INTERNAL_POINT,
    ("R1", "DOWNSTREAM_CHOKE"): ChartAreaFlag.INTERNAL_POINT,
    ("R1", "INDIVIDUAL_ASV_RATE"): ChartAreaFlag.INTERNAL_POINT,
    ("R1", "INDIVIDUAL_ASV_PRESSURE"): ChartAreaFlag.INTERNAL_POINT,
    ("R1", "COMMON_ASV"): ChartAreaFlag.INTERNAL_POINT,
    # R2 — below minimum flow (anti-surge kicks in)
    ("R2", "UPSTREAM_CHOKE"): ChartAreaFlag.BELOW_MINIMUM_FLOW_RATE,
    ("R2", "DOWNSTREAM_CHOKE"): ChartAreaFlag.BELOW_MINIMUM_FLOW_RATE,
    ("R2", "INDIVIDUAL_ASV_RATE"): ChartAreaFlag.BELOW_MINIMUM_FLOW_RATE,
    ("R2", "INDIVIDUAL_ASV_PRESSURE"): ChartAreaFlag.BELOW_MINIMUM_FLOW_RATE,
    ("R2", "COMMON_ASV"): ChartAreaFlag.BELOW_MINIMUM_FLOW_RATE,
    # R3 — below minimum flow at min speed
    ("R3", "UPSTREAM_CHOKE"): ChartAreaFlag.BELOW_MINIMUM_FLOW_RATE,
    ("R3", "DOWNSTREAM_CHOKE"): ChartAreaFlag.BELOW_MINIMUM_FLOW_RATE,
    ("R3", "INDIVIDUAL_ASV_RATE"): ChartAreaFlag.BELOW_MINIMUM_FLOW_RATE,
    ("R3", "INDIVIDUAL_ASV_PRESSURE"): ChartAreaFlag.BELOW_MINIMUM_FLOW_RATE,
    ("R3", "COMMON_ASV"): ChartAreaFlag.BELOW_MINIMUM_FLOW_RATE,
    # R4 — target pressure unreachable, but operating point is internal at max speed
    ("R4", "UPSTREAM_CHOKE"): ChartAreaFlag.INTERNAL_POINT,
    ("R4", "DOWNSTREAM_CHOKE"): ChartAreaFlag.INTERNAL_POINT,
    ("R4", "INDIVIDUAL_ASV_RATE"): ChartAreaFlag.INTERNAL_POINT,
    ("R4", "INDIVIDUAL_ASV_PRESSURE"): ChartAreaFlag.INTERNAL_POINT,
    ("R4", "COMMON_ASV"): ChartAreaFlag.INTERNAL_POINT,
    # R5 — above maximum flow
    ("R5", "UPSTREAM_CHOKE"): ChartAreaFlag.ABOVE_MAXIMUM_FLOW_RATE,
    ("R5", "DOWNSTREAM_CHOKE"): ChartAreaFlag.ABOVE_MAXIMUM_FLOW_RATE,
    ("R5", "INDIVIDUAL_ASV_RATE"): ChartAreaFlag.ABOVE_MAXIMUM_FLOW_RATE,
    ("R5", "INDIVIDUAL_ASV_PRESSURE"): ChartAreaFlag.ABOVE_MAXIMUM_FLOW_RATE,
    ("R5", "COMMON_ASV"): ChartAreaFlag.ABOVE_MAXIMUM_FLOW_RATE,
    # R6 — internal point near max speed
    ("R6", "UPSTREAM_CHOKE"): ChartAreaFlag.INTERNAL_POINT,
    ("R6", "DOWNSTREAM_CHOKE"): ChartAreaFlag.INTERNAL_POINT,
    ("R6", "INDIVIDUAL_ASV_RATE"): ChartAreaFlag.INTERNAL_POINT,
    ("R6", "INDIVIDUAL_ASV_PRESSURE"): ChartAreaFlag.INTERNAL_POINT,
    ("R6", "COMMON_ASV"): ChartAreaFlag.INTERNAL_POINT,
    # R7 — internal point at min speed
    ("R7", "UPSTREAM_CHOKE"): ChartAreaFlag.INTERNAL_POINT,
    ("R7", "DOWNSTREAM_CHOKE"): ChartAreaFlag.INTERNAL_POINT,
    ("R7", "INDIVIDUAL_ASV_RATE"): ChartAreaFlag.INTERNAL_POINT,
    ("R7", "INDIVIDUAL_ASV_PRESSURE"): ChartAreaFlag.INTERNAL_POINT,
    ("R7", "COMMON_ASV"): ChartAreaFlag.INTERNAL_POINT,
    # R8 — zero rate, not calculated
    ("R8", "UPSTREAM_CHOKE"): ChartAreaFlag.NOT_CALCULATED,
    ("R8", "DOWNSTREAM_CHOKE"): ChartAreaFlag.NOT_CALCULATED,
    ("R8", "INDIVIDUAL_ASV_RATE"): ChartAreaFlag.NOT_CALCULATED,
    ("R8", "INDIVIDUAL_ASV_PRESSURE"): ChartAreaFlag.NOT_CALCULATED,
    ("R8", "COMMON_ASV"): ChartAreaFlag.NOT_CALCULATED,
    # R9 — internal point except UPSTREAM_CHOKE (above max flow)
    ("R9", "UPSTREAM_CHOKE"): ChartAreaFlag.ABOVE_MAXIMUM_FLOW_RATE,
    ("R9", "DOWNSTREAM_CHOKE"): ChartAreaFlag.INTERNAL_POINT,
    ("R9", "INDIVIDUAL_ASV_RATE"): ChartAreaFlag.INTERNAL_POINT,
    ("R9", "INDIVIDUAL_ASV_PRESSURE"): ChartAreaFlag.INTERNAL_POINT,
    ("R9", "COMMON_ASV"): ChartAreaFlag.INTERNAL_POINT,
}


def _safe_delta(left: float, right: float) -> float:
    if isnan(left) or isnan(right):
        return 0.0
    return left - right


@pytest.mark.parametrize("case", TEST_CASES, ids=lambda case: case.id)
def test_legacy_solver_path(
    case: TrialCase,
    variable_speed_compressor_chart_data,
    legacy_train_factory,
):
    train = legacy_train_factory(
        chart_data=variable_speed_compressor_chart_data,
        pressure_control=FixedSpeedPressureControl(case.mode),
    )
    result = train.evaluate_given_constraints(
        CompressorTrainEvaluationInput(
            rates=[case.region.rate_sm3_day],
            suction_pressure=case.region.suction_pressure_bara,
            discharge_pressure=case.region.discharge_pressure_bara,
        )
    )
    stage_result = result.stage_results[0]
    speed = result.speed if not isnan(result.speed) else train.shaft.get_speed()

    assert result.is_valid is case.expectation.success
    assert _LEGACY_TO_OUTCOME[result.failure_status] is case.expectation.outcome
    assert_pressure_expectation(result.discharge_pressure, case)
    assert_speed_boundary(speed, variable_speed_compressor_chart_data, case)
    assert result.power_megawatt == pytest.approx(case.expectation.power_mw, abs=POWER_TOLERANCE)
    expected_chart_area = LEGACY_CHART_AREAS.get((case.region.id, case.mode))
    if expected_chart_area is not None:
        assert result.chart_area_status is expected_chart_area

    recirculation_rate = _safe_delta(
        stage_result.standard_rate_asv_corrected_sm3_per_day,
        stage_result.standard_rate_sm3_per_day,
    )
    assert_control_behavior(
        case,
        recirculation_rates=(recirculation_rate,),
        anti_surge_recirculation_rates=(recirculation_rate,) if case.region.expect_auto_anti_surge else (),
        suction_pressure_after_upstream_choke_bara=(
            stage_result.inlet_stream.pressure_bara if stage_result.inlet_stream is not None else None
        ),
    )
