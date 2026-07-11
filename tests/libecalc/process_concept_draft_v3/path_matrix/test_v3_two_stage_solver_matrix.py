"""v3 two-stage solver-path matrix: 30 cases vs the legacy golden snapshot.

6 regions × 5 modes = 30 test cases for a two-stage LP + HP compressor train
sharing a single variable-speed shaft. Reuses the same case definitions and
golden snapshot as the process-solver two-stage matrix.
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
from tests.libecalc.process.process_solver.compressor_solver_path_matrix.two_stage_solver_path_matrix.assertions import (  # noqa: E501
    assert_pressure_expectation as assert_two_stage_pressure_expectation,
)
from tests.libecalc.process.process_solver.compressor_solver_path_matrix.two_stage_solver_path_matrix.assertions import (
    assert_speed_boundary as assert_two_stage_speed_boundary,
)
from tests.libecalc.process.process_solver.compressor_solver_path_matrix.two_stage_solver_path_matrix.assertions import (
    assert_stage_power as assert_two_stage_stage_power,
)
from tests.libecalc.process.process_solver.compressor_solver_path_matrix.two_stage_solver_path_matrix.assertions import (
    assert_stage_recirculation as assert_two_stage_stage_recirculation,
)
from tests.libecalc.process.process_solver.compressor_solver_path_matrix.two_stage_solver_path_matrix.cases import (
    TEST_CASES as TWO_STAGE_TEST_CASES,
)
from tests.libecalc.process.process_solver.compressor_solver_path_matrix.two_stage_solver_path_matrix.cases import (
    TwoStageTrialCase,
)
from tests.libecalc.process.process_solver.compressor_solver_path_matrix.utils import (
    POWER_TOLERANCE,
    ExpectedOutcome,
)
from tests.libecalc.process_concept_draft_v3.conftest import V3System


@dataclass(frozen=True)
class _Xfail:
    reason: str


# Cases where v3 diverges from legacy — remove entries as v3 improves.
V3_TWO_STAGE_XFAILS: dict[tuple[str, str], _Xfail] = {
    # Power divergence: upstream choke at over-compression region.
    ("M1", "UPSTREAM_CHOKE"): _Xfail("Upstream choke power diverges from legacy (5.38 vs 5.23 MW)."),
    # Common ASV power divergences: the common loop drives different recirculation
    # distribution than legacy, producing different per-stage power splits.
    ("M1", "COMMON_ASV"): _Xfail("Common-ASV power diverges from legacy (5.98 vs 6.39 MW)."),
    ("M2", "COMMON_ASV"): _Xfail("Common-ASV power diverges from legacy (5.98 vs 6.39 MW)."),
    ("M4", "COMMON_ASV"): _Xfail("Common-ASV power diverges from legacy (11.88 vs 11.19 MW)."),
}


def _make_param(case: TwoStageTrialCase):
    xfail = V3_TWO_STAGE_XFAILS.get((case.region.id, case.mode))
    if xfail is None:
        return pytest.param(case, id=case.id)
    return pytest.param(case, id=case.id, marks=pytest.mark.xfail(reason=xfail.reason, strict=True))


PARAMS = tuple(_make_param(case) for case in TWO_STAGE_TEST_CASES)


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


def _speed(result, built) -> float:
    param = Param(built.shaft, "speed")
    if param in result.values:
        return result.values[param]
    return speed_bounds(built.system, built.shaft).lower


def _per_stage_power_mw(result, built: V3System) -> tuple[float, ...]:
    """Per-stage power from v3 operating points."""
    if result.state is None or not result.state.feasible:
        return ()
    powers = []
    for stage in built.stages:
        if stage in result.state.operating_points:
            powers.append(result.state.result(stage).power_mw)
        else:
            powers.append(math.nan)
    return tuple(powers)


def _per_stage_recirculation(result, built: V3System) -> tuple[float, ...]:
    """Per-stage recirculation rates from v3 solver values + auto values."""
    rates = []
    for stage in built.stages:
        param = Param(stage, "recirculation_rate")
        rate = result.values.get(param, 0.0) + result.auto_values.get(param, 0.0)
        rates.append(rate)
    # Also check common loop rate
    if built.loop is not None:
        loop_param = Param(built.loop, "rate_sm3_per_day")
        loop_rate = result.values.get(loop_param, 0.0) + result.auto_values.get(loop_param, 0.0)
        return (loop_rate,)
    return tuple(rates)


@pytest.mark.parametrize("case", PARAMS)
def test_v3_two_stage_solver_path(
    case: TwoStageTrialCase,
    variable_speed_compressor_chart_data,
    hp_compressor_chart_data,
    v3_two_stage_case_factory,
):
    # ── Arrange ──────────────────────────────────────────────────────────
    built, constraint, inlet = v3_two_stage_case_factory(
        lp_chart_data=variable_speed_compressor_chart_data,
        hp_chart_data=hp_compressor_chart_data,
        case=case,
    )

    # ── Act ──────────────────────────────────────────────────────────────
    result = solve(built.system, [constraint], {"feed": inlet})

    # ── Assert: outcome ──────────────────────────────────────────────────
    assert result.success is case.expectation.success
    assert _outcome(result) is case.expectation.outcome

    # ── Assert: pressure and speed ───────────────────────────────────────
    outlet_pressure = _outlet_pressure(result, built.target_unit)
    assert_two_stage_pressure_expectation(outlet_pressure, case)

    if case.expectation.success:
        assert_two_stage_speed_boundary(_speed(result, built), variable_speed_compressor_chart_data, case)

    # ── Assert: per-stage power ──────────────────────────────────────────
    per_stage_power = _per_stage_power_mw(result, built)
    if per_stage_power and case.expectation.power_mw is not None:
        assert sum(per_stage_power) == pytest.approx(case.expectation.power_mw, abs=POWER_TOLERANCE)
        assert_two_stage_stage_power(case, per_stage_power)

    # ── Assert: per-stage recirculation ──────────────────────────────────
    if case.expectation.success:
        recirculation_rates = _per_stage_recirculation(result, built)
        assert_two_stage_stage_recirculation(case, recirculation_rates)
