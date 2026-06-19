"""v3 single-stage solver-path matrix: 45 cases vs the legacy golden snapshot.

Policy (decision D7): the existing solver's pass/xfail pattern is the FLOOR. R8
(zero rate) is FIXED in v3 (the idle convention is implemented in ``solve``). R1/R6
(min/max-speed boundary brackets) are ATTEMPTED; cases that still diverge are marked
strict-xfail with the harness's reason.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import pytest

from libecalc.process_concept_draft_v3.params import Param
from libecalc.process_concept_draft_v3.solver import (
    RateTooHighFailure,
    RateTooLowFailure,
    TargetDirection,
    TargetUnreachableFailure,
    solve,
    speed_bounds,
)

from .conftest import (
    POWER_TOLERANCE,
    TEST_CASES,
    ExpectedOutcome,
    TrialCase,
    assert_pressure_expectation,
    assert_speed_boundary,
)


@dataclass(frozen=True)
class _Xfail:
    reason: str


# R8 is fixed in v3 (no entry). R1/R6 attempted; entries here remain if v3 still diverges.
V3_XFAILS: dict[tuple[str, str], _Xfail] = {}


def _make_param(case: TrialCase):
    xfail = V3_XFAILS.get((case.region.id, case.mode))
    if xfail is None:
        return pytest.param(case, id=case.id)
    return pytest.param(case, id=case.id, marks=pytest.mark.xfail(reason=xfail.reason, strict=True))


PARAMS = tuple(_make_param(case) for case in TEST_CASES)


def _outcome(result) -> ExpectedOutcome:
    if result.success:
        return ExpectedOutcome.SUCCESS
    failure = result.failure
    if isinstance(failure, RateTooHighFailure):
        return ExpectedOutcome.ABOVE_MAX_FLOW
    if isinstance(failure, RateTooLowFailure):
        return ExpectedOutcome.BELOW_MIN_FLOW
    if isinstance(failure, TargetUnreachableFailure):
        if failure.direction is TargetDirection.MAX_BELOW_TARGET:
            return ExpectedOutcome.PRESSURE_TOO_HIGH
        return ExpectedOutcome.PRESSURE_TOO_LOW
    return ExpectedOutcome.NOT_CALCULATED


def _outlet_pressure(result, target_unit) -> float:
    if result.state is None or not result.state.feasible:
        return math.nan
    try:
        return result.state.out(target_unit).pressure_bara
    except KeyError:
        return math.nan


def _speed(result, built, chart_data) -> float:
    param = Param(built.shaft, "speed")
    if param in result.values:
        return result.values[param]
    return speed_bounds(built.system, built.shaft).lower


@pytest.mark.parametrize("case", PARAMS)
def test_v3_solver_path(case: TrialCase, variable_speed_compressor_chart_data, v3_case_factory):
    built, constraint, inlet = v3_case_factory(chart_data=variable_speed_compressor_chart_data, case=case)
    result = solve(built.system, [constraint], {"feed": inlet})

    assert result.success is case.expectation.success
    assert _outcome(result) is case.expectation.outcome

    outlet_pressure = _outlet_pressure(result, built.target_unit)
    assert_pressure_expectation(outlet_pressure, case)

    if case.region.speed_boundary_class.value != "not_asserted":
        assert_speed_boundary(
            _speed(result, built, variable_speed_compressor_chart_data), variable_speed_compressor_chart_data, case
        )

    # Power: assert only when a feasible operating point exists and the golden has a value.
    if (
        case.expectation.power_mw is not None
        and result.state is not None
        and result.state.feasible
        and built.stages[0] in result.state.operating_points
    ):
        power_mw = result.state.result(built.stages[0]).power_mw
        assert power_mw == pytest.approx(case.expectation.power_mw, abs=POWER_TOLERANCE)
