from libecalc.domain.infrastructure.energy_components.legacy_consumer.tabulated import TabularConsumerFunction
from libecalc.domain.infrastructure.energy_components.legacy_consumer.tabulated.common import (
    VariableExpression,
)
from libecalc.domain.variable import Variable
from libecalc.expression import Expression


def test_tabular_consumer_single_period_returns_list(
    condition_factory,
    regularity_factory,
    expression_evaluator_factory,
    power_loss_factor_factory,
):
    # Minimal setup: one variable, one function value
    headers = ["RATE", "FUEL"]
    data = [[1.0], [10.0]]  # Variable value and function value
    variables_expressions = [VariableExpression(name="RATE", expression=Expression.setup_from_expression("RATE"))]
    variable = Variable(
        name="RATE",
        expression="RATE",
        expression_evaluator=expression_evaluator_factory.default(),
        regularity=regularity_factory(expression_evaluator=expression_evaluator_factory.default()),
    )
    consumer_function = TabularConsumerFunction(
        headers=headers,
        data=data,
        energy_usage_adjustment_constant=0.0,
        energy_usage_adjustment_factor=1.0,
        variables=[variable],
        power_loss_factor=power_loss_factor_factory(),
        condition=condition_factory(),
        regularity=regularity_factory(),
    )

    # Test with a single variable and a single value (e.g. only one period).
    # Ensures that the function returns a flat list (not a scalar)
    # even when only one period and one value are present.
    rate_input = Variable(
        name="RATE",
        expression="1.0",
        expression_evaluator=expression_evaluator_factory.default(),
        regularity=regularity_factory(expression_evaluator=expression_evaluator_factory.default()),
    )
    result = consumer_function.evaluate_variables([rate_input])
    assert isinstance(result.energy_usage, list)
    assert result.energy_usage == [10.0]
