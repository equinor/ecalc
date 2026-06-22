"""Shared assertion helpers for two-stage solver-path matrix tests."""

from __future__ import annotations

from math import isnan

import pytest

from libecalc.domain.process.value_objects.chart.chart import ChartData

from ..utils import (
    POWER_TOLERANCE,
    RECIRCULATION_THRESHOLD,
    ExpectedControlAction,
    PressureExpectation,
    SpeedBoundaryClass,
)
from .cases import TwoStageTrialCase

PRESSURE_TOLERANCE = 2e-3  # tighter than the shared 0.01; two-stage converges well enough


def assert_pressure_expectation(outlet_pressure_bara: float, case: TwoStageTrialCase) -> None:
    """Assert outlet pressure matches the expected relationship to target."""
    expected = case.region.discharge_pressure_bara
    expectation = case.expectation.pressure_expectation
    if expectation is PressureExpectation.TARGET:
        assert outlet_pressure_bara == pytest.approx(expected, abs=PRESSURE_TOLERANCE)
    elif expectation is PressureExpectation.ABOVE_TARGET:
        assert outlet_pressure_bara > expected
    elif expectation is PressureExpectation.BELOW_TARGET:
        assert outlet_pressure_bara < expected
    elif expectation is PressureExpectation.NAN:
        assert isnan(outlet_pressure_bara)
    elif expectation is PressureExpectation.NOT_ASSERTED:
        return
    else:
        raise AssertionError(f"Unexpected pressure expectation: {expectation}")


def assert_speed_boundary(speed: float, chart_data: ChartData, case: TwoStageTrialCase) -> None:
    """Assert shaft speed is at the expected boundary (min/max/internal)."""
    boundary_class = case.region.speed_boundary_class
    if boundary_class is SpeedBoundaryClass.NOT_ASSERTED:
        return

    speeds = [curve.speed for curve in chart_data.get_adjusted_curves()]
    minimum_speed = min(speeds)
    maximum_speed = max(speeds)
    if boundary_class is SpeedBoundaryClass.MINIMUM:
        assert speed == pytest.approx(minimum_speed, rel=1e-4)
    elif boundary_class is SpeedBoundaryClass.MAXIMUM:
        assert speed == pytest.approx(maximum_speed, rel=1e-4)
    elif boundary_class is SpeedBoundaryClass.INTERNAL:
        assert minimum_speed < speed < maximum_speed
    else:
        raise AssertionError(f"Unexpected speed boundary class: {boundary_class}")


def assert_control_behavior(
    case: TwoStageTrialCase,
    *,
    suction_pressure_after_upstream_choke_bara: float | None = None,
) -> None:
    """Assert the train-level pressure-control mechanism behaved as expected.

    Only the choke is a train-level unit, so only choke behavior is checked here.
    Per-stage anti-surge recirculation is asserted by ``assert_stage_recirculation``.
    """
    if not case.expectation.success:
        return

    if case.expectation.control_action is ExpectedControlAction.UPSTREAM_CHOKE:
        if suction_pressure_after_upstream_choke_bara is not None:
            assert suction_pressure_after_upstream_choke_bara < case.region.suction_pressure_bara, (
                f"Upstream choke should reduce suction pressure: "
                f"{suction_pressure_after_upstream_choke_bara} >= {case.region.suction_pressure_bara}"
            )


def assert_stage_recirculation(
    case: TwoStageTrialCase,
    recirculation_rates: tuple[float, ...],
) -> None:
    """Assert each stage recirculates iff its ``StageExpectation`` says so.

    ``recirculation_rates`` holds one rate per recirculation loop:

    * **One loop per stage** — per-compressor loops (legacy always; process for
      every mode except COMMON_ASV). Each stage is checked against its own intent.
    * **A single train-wide loop** — COMMON_ASV wraps the whole train in one loop,
      so only the aggregate ("any stage recirculates") is observable.
    """
    if not case.expectation.success:
        return

    stage_intents = [stage.recirculates for stage in case.stages]

    if len(recirculation_rates) == len(case.stages):
        for stage_index, (intent, rate) in enumerate(zip(stage_intents, recirculation_rates, strict=True)):
            if intent is None:
                continue
            has_recirc = rate > RECIRCULATION_THRESHOLD
            assert has_recirc == intent, (
                f"{case.id} stage {stage_index}: recirculation rate {rate} contradicts expected recirculates={intent}"
            )
        return

    # Single train-wide loop (COMMON_ASV): only the aggregate is observable.
    expected_any_stage = any(intent for intent in stage_intents if intent is not None)
    actual_any_recirc = any(rate > RECIRCULATION_THRESHOLD for rate in recirculation_rates)
    assert actual_any_recirc == expected_any_stage, (
        f"{case.id}: train-wide recirculation {recirculation_rates} "
        f"contradicts expected any-stage recirculates={expected_any_stage}"
    )


def assert_stage_power(
    case: TwoStageTrialCase,
    per_stage_power_mw: tuple[float, ...],
) -> None:
    """Assert each stage's power matches its golden per-stage expectation."""
    for stage_index, (stage, power) in enumerate(zip(case.stages, per_stage_power_mw, strict=True)):
        if stage.power_mw is None:
            continue
        assert power == pytest.approx(stage.power_mw, abs=POWER_TOLERANCE), (
            f"{case.id} stage {stage_index}: power {power} MW but expected {stage.power_mw} MW"
        )
