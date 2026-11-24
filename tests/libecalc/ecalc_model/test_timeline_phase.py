from datetime import datetime

import pytest

from libecalc.common.time_utils import Periods
from libecalc.common.variables import VariablesMap
from libecalc.ecalc_model.timeline_phase import (
    TimelinePhase,
    TimelinePhaseNotBinaryException,
    TimelinePhaseNotFoundException,
    TimelinePhaseService,
    TimelinePhaseType,
)
from libecalc.expression.expression import Expression
from libecalc.presentation.yaml.domain.expression_timeline_phase_condition import ExpressionTimelinePhaseCondition


def _phase(reference: str, when: str) -> TimelinePhase:
    return TimelinePhase(
        reference=reference,
        title=reference,
        type=TimelinePhaseType.PRODUCTION,
        when=ExpressionTimelinePhaseCondition(Expression.setup_from_expression(when)),
        description=None,
    )


@pytest.fixture
def expression_evaluator() -> VariablesMap:
    """Three yearly periods with a drilling flag and a gas production rate."""
    periods = Periods.create_periods(
        [datetime(2025, 1, 1), datetime(2026, 1, 1), datetime(2027, 1, 1), datetime(2028, 1, 1)],
        include_before=False,
        include_after=False,
    )
    return VariablesMap(periods=periods, variables={"SIM;DRILLING_FLAG": [1, 1, 0], "SIM;GAS_PROD": [0, 5, 10]})


def test_get_phase_by_unknown_reference_raises():
    service = TimelinePhaseService(timeline_phases=[_phase("production", "SIM;GAS_PROD > 0")])

    with pytest.raises(TimelinePhaseNotFoundException):
        service.get_phase_by_reference("unknown")


def test_is_active_from_flag(expression_evaluator):
    service = TimelinePhaseService(timeline_phases=[_phase("drilling", "SIM;DRILLING_FLAG")])

    assert service.is_active("drilling", expression_evaluator) == [True, True, False]


def test_is_active_raises_when_not_0_or_1(expression_evaluator):
    service = TimelinePhaseService(timeline_phases=[_phase("production", "SIM;GAS_PROD")])

    with pytest.raises(TimelinePhaseNotBinaryException, match="got 5, 10"):
        service.is_active("production", expression_evaluator)
