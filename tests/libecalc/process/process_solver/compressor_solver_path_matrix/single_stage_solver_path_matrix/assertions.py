"""Shared assertion helpers for solver-path matrix tests."""

from __future__ import annotations

from math import isnan

import pytest

from libecalc.domain.process.value_objects.chart.chart import ChartData

# Shared tolerances/vocabulary live in the common parent package.
from ..utils import (  # noqa: F401  (POWER_TOLERANCE/PRESSURE_TOLERANCE re-exported for tests importing from this module)
    POWER_TOLERANCE,
    PRESSURE_TOLERANCE,
    RECIRCULATION_THRESHOLD,
    ExpectedControlAction,
    PressureExpectation,
    SpeedBoundaryClass,
)
from .cases import TrialCase


def assert_pressure_expectation(outlet_pressure_bara: float, case: TrialCase) -> None:
    expected_pressure = case.region.discharge_pressure_bara
    expectation = case.expectation.pressure_expectation
    if expectation is PressureExpectation.TARGET:
        assert outlet_pressure_bara == pytest.approx(expected_pressure, abs=PRESSURE_TOLERANCE)
    elif expectation is PressureExpectation.ABOVE_TARGET:
        assert outlet_pressure_bara > expected_pressure
    elif expectation is PressureExpectation.BELOW_TARGET:
        assert outlet_pressure_bara < expected_pressure
    elif expectation is PressureExpectation.NAN:
        assert isnan(outlet_pressure_bara)
    elif expectation is PressureExpectation.NOT_ASSERTED:
        return
    else:
        raise AssertionError(f"Unexpected pressure expectation: {expectation}")


def assert_speed_boundary(speed: float, chart_data: ChartData, case: TrialCase) -> None:
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
    case: TrialCase,
    *,
    recirculation_rates: tuple[float, ...],
    anti_surge_recirculation_rates: tuple[float, ...],
    choke_delta_pressure: float | None = None,
) -> None:
    has_recirculation = any(rate > RECIRCULATION_THRESHOLD for rate in recirculation_rates)
    has_anti_surge_recirculation = any(rate > RECIRCULATION_THRESHOLD for rate in anti_surge_recirculation_rates)

    if case.region.expect_auto_anti_surge:
        assert has_anti_surge_recirculation
    elif case.expectation.success and case.mode in {"DOWNSTREAM_CHOKE", "UPSTREAM_CHOKE"}:
        assert not has_anti_surge_recirculation

    action = case.expectation.control_action
    if action is ExpectedControlAction.RECIRCULATION:
        assert has_recirculation

    if action is ExpectedControlAction.DOWNSTREAM_CHOKE:
        assert choke_delta_pressure is None or choke_delta_pressure > 0.0
    elif action is ExpectedControlAction.UPSTREAM_CHOKE:
        assert choke_delta_pressure is None or choke_delta_pressure > 0.0
    elif choke_delta_pressure is not None:
        assert choke_delta_pressure == pytest.approx(0.0, abs=PRESSURE_TOLERANCE)
