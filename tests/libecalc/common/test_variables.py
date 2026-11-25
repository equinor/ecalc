from datetime import datetime

import pytest

from libecalc.common.time_utils import Periods
from libecalc.common.variables import ExpressionCannotEvaluateToBooleanValueException, VariablesMap
from libecalc.expression.expression import Expression


@pytest.fixture
def expression_evaluator() -> VariablesMap:
    periods = Periods.create_periods(
        [datetime(2025, 1, 1), datetime(2026, 1, 1), datetime(2027, 1, 1), datetime(2028, 1, 1)],
        include_before=False,
        include_after=False,
    )
    return VariablesMap(periods=periods, variables={"SIM;FLAG": [1, 0, 1], "SIM;RATE": [0, 5, 10]})


@pytest.mark.parametrize(
    "expression, expected",
    [
        ("SIM;FLAG", [True, False, True]),
        ("SIM;RATE > 0", [False, True, True]),
        (True, [True, True, True]),
        (False, [False, False, False]),
    ],
)
def test_evaluate_boolean(expression_evaluator, expression, expected):
    values = expression_evaluator.evaluate_boolean(Expression.setup_from_expression(expression))

    assert values.tolist() == expected


def test_evaluate_boolean_raises_when_not_1_or_0(expression_evaluator):
    with pytest.raises(ExpressionCannotEvaluateToBooleanValueException, match="got 5, 10") as exc_info:
        expression_evaluator.evaluate_boolean(Expression.setup_from_expression("SIM;RATE"))

    assert exc_info.value.invalid_values == [5, 10]
