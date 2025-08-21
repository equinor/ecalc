from datetime import datetime

from libecalc.domain.infrastructure.energy_components.legacy_consumer.tabulated import TabularConsumerFunction
from libecalc.domain.regularity import Regularity
from libecalc.presentation.yaml.domain.expression_time_series_variable import ExpressionTimeSeriesVariable
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression
from tests.conftest import expression_evaluator_factory


def test_tabular_consumer_single_period_returns_list(expression_evaluator_factory):
    test_time_vector = [datetime(2020, 1, 1), datetime(2030, 1, 1)]
    # Minimal setup: one variable, one function value
    headers = ["RATE", "FUEL"]
    data = [[1.0], [10.0]]  # Variable value and function value

    expression_evaluator = expression_evaluator_factory.from_time_vector(test_time_vector)
    regularity = Regularity(
        expression_evaluator=expression_evaluator, target_period=expression_evaluator.get_period(), expression_input=1
    )

    variables = ExpressionTimeSeriesVariable(
        name="RATE",
        time_series_expression=TimeSeriesExpression(expressions="RATE", expression_evaluator=expression_evaluator),
        regularity=regularity,
    )
    consumer_function = TabularConsumerFunction(
        headers=headers,
        data=data,
        energy_usage_adjustment_constant=0.0,
        energy_usage_adjustment_factor=1.0,
        variables=[variables],
    )

    # Test with a single variable and a single value (e.g. only one period).
    # Ensures that the function returns a flat list (not a scalar)
    # even when only one period and one value are present.
    rate_input = ExpressionTimeSeriesVariable(
        name="RATE",
        time_series_expression=TimeSeriesExpression(expressions="1.0", expression_evaluator=expression_evaluator),
        regularity=regularity,
    )

    result = consumer_function.evaluate_variables([rate_input])
    assert isinstance(result.energy_usage, list)
    assert result.energy_usage == [10.0]
