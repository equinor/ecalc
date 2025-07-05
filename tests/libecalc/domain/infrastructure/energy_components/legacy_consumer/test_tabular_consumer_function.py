from libecalc.domain.condition import Condition
from libecalc.domain.infrastructure.energy_components.legacy_consumer.tabulated import TabularConsumerFunction
from libecalc.domain.infrastructure.energy_components.legacy_consumer.tabulated.common import (
    Variable,
    VariableExpression,
)
from libecalc.expression import Expression


def test_tabular_consumer_single_period_returns_list():
    # Minimal setup: one variable, one function value
    headers = ["RATE", "FUEL"]
    data = [[1.0], [10.0]]  # Variable value and function value
    variables_expressions = [VariableExpression(name="RATE", expression=Expression.setup_from_expression("RATE"))]

    consumer_function = TabularConsumerFunction(
        headers=headers,
        data=data,
        energy_usage_adjustment_constant=0.0,
        energy_usage_adjustment_factor=1.0,
        variables_expressions=variables_expressions,
        power_loss_factor_expression=None,
    )

    # Test with a single variable and a single value (e.g. only one period).
    # Ensures that the function returns a flat list (not a scalar)
    # even when only one period and one value are present.
    rate_input = [Variable(name="RATE", values=[1.0])]

    result = consumer_function.evaluate_variables(rate_input)
    assert isinstance(result.energy_usage, list)
    assert result.energy_usage == [10.0]
