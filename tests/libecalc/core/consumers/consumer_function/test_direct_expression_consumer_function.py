from datetime import datetime

import numpy as np
import pytest

import libecalc.common.energy_usage_type
import libecalc.common.utils.rates
from libecalc.common.component_type import ComponentType
from libecalc.common.consumption_type import ConsumptionType
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period
from libecalc.common.variables import VariablesMap
from libecalc.domain.infrastructure.energy_components.legacy_consumer.component import Consumer
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function.direct_expression_consumer_function import (
    DirectExpressionConsumerFunction,
)
from libecalc.domain.regularity import Regularity
from libecalc.expression import Expression
from libecalc.presentation.yaml.domain.expression_time_series_flow_rate import ExpressionTimeSeriesFlowRate
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


@pytest.fixture
def direct_variables_map(expression_evaluator_factory) -> VariablesMap:
    time_vector = [
        datetime(2000, 1, 1),
        datetime(2001, 1, 1),
        datetime(2003, 1, 1),
    ]
    return expression_evaluator_factory.from_time_vector(variables={"foo;bar": [1.0, 1.0]}, time_vector=time_vector)


def test_direct_expression_consumer_function(expression_evaluator_factory):
    time_series_name = "SIM1"

    # Test evaluation
    variables_map = expression_evaluator_factory.from_time_vector(
        time_vector=[
            datetime(2000, 1, 1, 0, 0),
            datetime(2001, 1, 1, 0, 0),
            datetime(2002, 1, 1, 0, 0),
        ],
        variables={"SIM1;Flare": [10.0, 3.0], "SIM1;Vent": [5.0, 2.0]},
    )
    regularity = Regularity(
        expression_input=1,
        target_period=Period(datetime(1900, 1, 1)),
        expression_evaluator=variables_map,
    )
    fuel_rate_expression = TimeSeriesExpression(
        expressions=time_series_name + ";Flare {+} " + time_series_name + ";Vent", expression_evaluator=variables_map
    )
    fuel_rate = ExpressionTimeSeriesFlowRate(time_series_expression=fuel_rate_expression, regularity=regularity)
    result = DirectExpressionConsumerFunction(
        fuel_rate=fuel_rate,
        energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.FUEL,
    ).evaluate(
        expression_evaluator=variables_map,
        regularity=regularity.get_values,
    )
    expected_result = [15, 5]
    np.testing.assert_allclose(result.energy_usage, expected_result)

    # Test when used as consumer function for a fuel consumer
    fuel_consumer = Consumer(
        id="Flare",
        name="Flare",
        component_type=ComponentType.GENERIC,
        energy_usage_model=TemporalModel(
            {
                Period(datetime(1900, 1, 1)): DirectExpressionConsumerFunction(
                    fuel_rate=fuel_rate,
                    energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.FUEL,
                )
            },
        ),
        consumes=ConsumptionType.FUEL,
        regularity=regularity,
    )
    result = fuel_consumer.evaluate(expression_evaluator=variables_map)
    consumer_result = result.component_result
    np.testing.assert_allclose(
        actual=consumer_result.energy_usage.values,
        desired=expected_result,
    )

    # Test with various input to expression
    # Constant
    fuel_rate_expression = TimeSeriesExpression(expressions="2", expression_evaluator=variables_map)
    fuel_rate = ExpressionTimeSeriesFlowRate(time_series_expression=fuel_rate_expression, regularity=regularity)

    np.testing.assert_allclose(
        actual=DirectExpressionConsumerFunction(
            fuel_rate=fuel_rate,
            energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.FUEL,
        )
        .evaluate(
            expression_evaluator=variables_map,
            regularity=regularity.get_values,
        )
        .energy_usage,
        desired=[2, 2],
    )
    # When expression string is float even if it should be string
    fuel_rate_expression = TimeSeriesExpression(expressions=2.1, expression_evaluator=variables_map)
    fuel_rate = ExpressionTimeSeriesFlowRate(time_series_expression=fuel_rate_expression, regularity=regularity)

    np.testing.assert_allclose(
        actual=DirectExpressionConsumerFunction(
            fuel_rate=fuel_rate,
            energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.FUEL,
        )
        .evaluate(
            expression_evaluator=variables_map,
            regularity=regularity.get_values,
        )
        .energy_usage,
        desired=[2.1, 2.1],
    )
    # Expression with numbers only
    fuel_rate_expression = TimeSeriesExpression(expressions="2 {+} 3.1", expression_evaluator=variables_map)
    fuel_rate = ExpressionTimeSeriesFlowRate(time_series_expression=fuel_rate_expression, regularity=regularity)

    np.testing.assert_allclose(
        actual=DirectExpressionConsumerFunction(
            fuel_rate=fuel_rate,
            energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.FUEL,
        )
        .evaluate(
            expression_evaluator=variables_map,
            regularity=[1.0] * variables_map.number_of_periods,
        )
        .energy_usage,
        desired=[5.1, 5.1],
    )
    # Expression with time series input
    fuel_rate_expression = TimeSeriesExpression(
        expressions="0 {*} " + time_series_name + ";Flare", expression_evaluator=variables_map
    )
    fuel_rate = ExpressionTimeSeriesFlowRate(time_series_expression=fuel_rate_expression, regularity=regularity)

    np.testing.assert_allclose(
        actual=DirectExpressionConsumerFunction(
            fuel_rate=fuel_rate,
            energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.FUEL,
        )
        .evaluate(
            expression_evaluator=variables_map,
            regularity=regularity.get_values,
        )
        .energy_usage,
        desired=[0, 0],
    )
    # Expression 0
    fuel_rate_expression = TimeSeriesExpression(expressions="0", expression_evaluator=variables_map)
    fuel_rate = ExpressionTimeSeriesFlowRate(time_series_expression=fuel_rate_expression, regularity=regularity)

    np.testing.assert_allclose(
        actual=DirectExpressionConsumerFunction(
            fuel_rate=fuel_rate,
            energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.FUEL,
        )
        .evaluate(
            expression_evaluator=variables_map,
            regularity=regularity.get_values,
        )
        .energy_usage,
        desired=[0, 0],
    )
    # With condition
    fuel_rate_expression = TimeSeriesExpression(expressions="2 {+} 3.1", expression_evaluator=variables_map)
    fuel_rate = ExpressionTimeSeriesFlowRate(
        time_series_expression=fuel_rate_expression,
        regularity=regularity,
        condition_expression=Expression.setup_from_expression(value="2 < 1"),
    )

    np.testing.assert_allclose(
        actual=DirectExpressionConsumerFunction(
            fuel_rate=fuel_rate,
            energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.FUEL,
            condition=Expression.setup_from_expression(value="2 < 1"),
        )
        .evaluate(
            expression_evaluator=variables_map,
            regularity=regularity.get_values,
        )
        .energy_usage,
        desired=[0, 0],
    )
    fuel_rate_expression = TimeSeriesExpression(expressions="3.1", expression_evaluator=variables_map)
    fuel_rate = ExpressionTimeSeriesFlowRate(
        time_series_expression=fuel_rate_expression,
        regularity=regularity,
        condition_expression=Expression.multiply(
            Expression.setup_from_expression(value="2 > 1"),
            Expression.setup_from_expression(value=time_series_name + ";Flare > 4"),
        ),
    )

    np.testing.assert_allclose(
        actual=DirectExpressionConsumerFunction(
            fuel_rate=fuel_rate,
            energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.FUEL,
            condition=Expression.multiply(
                Expression.setup_from_expression(value="2 > 1"),
                Expression.setup_from_expression(value=time_series_name + ";Flare > 4"),
            ),
        )
        .evaluate(
            expression_evaluator=variables_map,
            regularity=regularity.get_values,
        )
        .energy_usage,
        desired=[3.1, 0],
    )
    # With power loss factor
    fuel_rate_expression = TimeSeriesExpression(expressions="2", expression_evaluator=variables_map)
    fuel_rate = ExpressionTimeSeriesFlowRate(time_series_expression=fuel_rate_expression, regularity=regularity)

    np.testing.assert_allclose(
        actual=DirectExpressionConsumerFunction(
            fuel_rate=fuel_rate,
            power_loss_factor=Expression.setup_from_expression(value=0.2),
            energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.FUEL,
        )
        .evaluate(
            expression_evaluator=variables_map,
            regularity=regularity.get_values,
        )
        .energy_usage,
        desired=[2.5, 2.5],
    )


def test_direct_expression_consumer_function_consumption_rate_type(direct_variables_map):
    stream_day_consumption = 10.0
    regularity_value = 0.9
    calendar_day_consumption = f"{stream_day_consumption} {{*}} {regularity_value}"

    regularity = Regularity(
        expression_input=regularity_value,
        expression_evaluator=direct_variables_map,
        target_period=direct_variables_map.get_period(),
    )
    # The stream day function passes through the evaluated expression directly
    # with no modification from regularity - as this is already of "stream day" type
    load_expression = TimeSeriesExpression(
        expressions=stream_day_consumption, expression_evaluator=direct_variables_map
    )
    load_stream_day = ExpressionTimeSeriesFlowRate(
        time_series_expression=load_expression,
        regularity=regularity,
        consumption_rate_type=libecalc.common.utils.rates.RateType.STREAM_DAY,
    )

    stream_day_function = DirectExpressionConsumerFunction(
        load=load_stream_day,
        energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.POWER,
    )
    # The calendar day function, divides the evaluated expression by regularity
    # to obtain "stream day" type as it is of "calendar day" type
    load_expression = TimeSeriesExpression(
        expressions=calendar_day_consumption, expression_evaluator=direct_variables_map
    )
    load_calendar_day = ExpressionTimeSeriesFlowRate(
        time_series_expression=load_expression,
        regularity=regularity,
        consumption_rate_type=libecalc.common.utils.rates.RateType.CALENDAR_DAY,
    )

    calendar_day_function = DirectExpressionConsumerFunction(
        load=load_calendar_day,
        energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.POWER,
    )

    stream_day_function_result = stream_day_function.evaluate(
        expression_evaluator=direct_variables_map,
        regularity=regularity.get_values,
    )
    calendar_day_function_result = calendar_day_function.evaluate(
        expression_evaluator=direct_variables_map,
        regularity=regularity.get_values,
    )

    # When regularity is used, all returned consumption values should be of stream day type
    # (as they are multiplied with regularity post calculations in the energy function)
    np.testing.assert_allclose(
        actual=calendar_day_function_result.energy_usage,
        desired=stream_day_function_result.energy_usage,
    )
