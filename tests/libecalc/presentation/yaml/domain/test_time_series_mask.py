from datetime import datetime

import numpy as np

from libecalc.common.time_utils import Period
from libecalc.domain.regularity import Regularity
from libecalc.presentation.yaml.domain.time_series_mask import TimeSeriesMask
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression
from libecalc.presentation.yaml.domain.expression_time_series_variable import ExpressionTimeSeriesVariable


periods = [
    Period(start=datetime(2020, 1, 1), end=datetime(2021, 1, 1)),
    Period(start=datetime(2021, 1, 1), end=datetime(2022, 1, 1)),
    Period(start=datetime(2022, 1, 1), end=datetime(2023, 1, 1)),
]


def test_time_series_mask_none():
    """Test that TimeSeriesMask with None mask returns the input array unchanged."""
    mask = TimeSeriesMask.from_array(None)
    arr = np.array([1, 2, 3])
    np.testing.assert_array_equal(mask.apply(arr), arr)


def test_time_series_mask_int_mask():
    """Test that TimeSeriesMask with integer mask applies masking correctly."""
    mask = TimeSeriesMask.from_array(np.array([1, 0, 1]))
    arr = np.array([10, 20, 30])
    np.testing.assert_array_equal(mask.apply(arr), [10, 0, 30])


def test_time_series_mask_float_mask():
    """Test that TimeSeriesMask with float mask applies masking (nonzero as 1, zero as 0)."""
    mask = TimeSeriesMask.from_array(np.array([0.5, 0.0, -2.1]))
    arr = np.array([7, 8, 9])
    np.testing.assert_array_equal(mask.apply(arr), [7, 0, 9])


def test_time_series_mask_condition_mask(expression_evaluator_factory):
    """Test that TimeSeriesExpression uses condition mask correctly."""
    evaluator = expression_evaluator_factory.from_periods(
        periods, variables={"SIM1;GAS_PROD": [10.0, 5.0, 10.0], "TEST_VAR": [1.0, 2.0, 3.0]}
    )

    expr = TimeSeriesExpression(expression="TEST_VAR", expression_evaluator=evaluator, condition="SIM1;GAS_PROD > 5")
    # The condition "SIM1;GAS_PROD > 5" results in a mask [1, 0, 1], which is applied to the values of TEST_VAR
    assert expr.get_masked_values() == [1, 0, 3]


def test_expression_time_series_variable_get_values_with_mask(expression_evaluator_factory):
    """Test that ExpressionTimeSeriesVariable applies mask to values as expected."""
    evaluator = expression_evaluator_factory.from_periods(
        periods, variables={"SIM1;GAS_PROD": [10.0, 5.0, 10.0], "TEST_VAR": [1.0, 2.0, 3.0]}
    )
    regularity = Regularity(expression_evaluator=evaluator, target_period=evaluator.get_period(), expression_input=1)
    expr = TimeSeriesExpression(expression="TEST_VAR", expression_evaluator=evaluator, condition="SIM1;GAS_PROD > 5")

    var = ExpressionTimeSeriesVariable(name="test", time_series_expression=expr, regularity=regularity, is_rate=False)
    # The mask [1, 0, 1], created from condition, is applied to [1.0, 2.0, 3.0], resulting in [1.0, 0.0, 3.0]
    assert var.get_values() == [1, 0, 3]
