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
from libecalc.infrastructure.energy_components.legacy_consumer.component import Consumer
from libecalc.core.consumers.legacy_consumer.consumer_function.direct_expression_consumer_function import (
    DirectExpressionConsumerFunction,
)
from libecalc.expression import Expression


@pytest.fixture
def direct_variables_map() -> VariablesMap:
    time_vector = [
        datetime(2000, 1, 1),
        datetime(2001, 1, 1),
        datetime(2003, 1, 1),
    ]
    return VariablesMap(variables={"foo;bar": [1.0, 1.0]}, time_vector=time_vector)


def test_direct_expression_consumer_function():
    time_series_name = "SIM1"

    # Test evaluation
    variables_map = VariablesMap(
        time_vector=[
            datetime(2000, 1, 1, 0, 0),
            datetime(2001, 1, 1, 0, 0),
            datetime(2002, 1, 1, 0, 0),
        ],
        variables={"SIM1;Flare": [10.0, 3.0], "SIM1;Vent": [5.0, 2.0]},
    )

    result = DirectExpressionConsumerFunction(
        fuel_rate=Expression.setup_from_expression(time_series_name + ";Flare {+} " + time_series_name + ";Vent"),
        energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.FUEL,
    ).evaluate(
        expression_evaluator=variables_map,
        regularity=[1.0] * variables_map.number_of_periods,
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
                    fuel_rate=Expression.setup_from_expression(
                        time_series_name + ";Flare {+} " + time_series_name + ";Vent"
                    ),
                    energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.FUEL,
                )
            },
        ),
        consumes=ConsumptionType.FUEL,
        regularity=TemporalModel({Period(datetime(1900, 1, 1)): Expression.setup_from_expression(1)}),
    )
    result = fuel_consumer.evaluate(expression_evaluator=variables_map)
    consumer_result = result.component_result
    np.testing.assert_allclose(
        actual=consumer_result.energy_usage.values,
        desired=expected_result,
    )

    # Test with various input to expression
    # Constant
    np.testing.assert_allclose(
        actual=DirectExpressionConsumerFunction(
            fuel_rate=Expression.setup_from_expression(value="2"),
            energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.FUEL,
        )
        .evaluate(
            expression_evaluator=variables_map,
            regularity=[1.0] * len(variables_map.time_vector),
        )
        .energy_usage,
        desired=[2, 2],
    )
    # When expression string is float even if it should be string
    np.testing.assert_allclose(
        actual=DirectExpressionConsumerFunction(
            fuel_rate=Expression.setup_from_expression(value=2.1),
            energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.FUEL,
        )
        .evaluate(
            expression_evaluator=variables_map,
            regularity=[1.0] * variables_map.number_of_periods,
        )
        .energy_usage,
        desired=[2.1, 2.1],
    )
    # Expression with numbers only
    np.testing.assert_allclose(
        actual=DirectExpressionConsumerFunction(
            fuel_rate=Expression.setup_from_expression(value="2 {+} 3.1"),
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
    np.testing.assert_allclose(
        actual=DirectExpressionConsumerFunction(
            fuel_rate=Expression.setup_from_expression(value="0 {*} " + time_series_name + ";Flare"),
            energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.FUEL,
        )
        .evaluate(
            expression_evaluator=variables_map,
            regularity=[1.0] * variables_map.number_of_periods,
        )
        .energy_usage,
        desired=[0, 0],
    )
    # Expression 0
    np.testing.assert_allclose(
        actual=DirectExpressionConsumerFunction(
            fuel_rate=Expression.setup_from_expression(value="0"),
            energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.FUEL,
        )
        .evaluate(
            expression_evaluator=variables_map,
            regularity=[1.0] * variables_map.number_of_periods,
        )
        .energy_usage,
        desired=[0, 0],
    )
    # With condition
    np.testing.assert_allclose(
        actual=DirectExpressionConsumerFunction(
            fuel_rate=Expression.setup_from_expression(value="2 {+} 3.1"),
            energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.FUEL,
            condition=Expression.setup_from_expression(value="2 < 1"),
        )
        .evaluate(
            expression_evaluator=variables_map,
            regularity=[1.0] * variables_map.number_of_periods,
        )
        .energy_usage,
        desired=[0, 0],
    )
    np.testing.assert_allclose(
        actual=DirectExpressionConsumerFunction(
            fuel_rate=Expression.setup_from_expression(value="3.1"),
            energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.FUEL,
            condition=Expression.multiply(
                Expression.setup_from_expression(value="2 > 1"),
                Expression.setup_from_expression(value=time_series_name + ";Flare > 4"),
            ),
        )
        .evaluate(
            expression_evaluator=variables_map,
            regularity=[1.0] * variables_map.number_of_periods,
        )
        .energy_usage,
        desired=[3.1, 0],
    )
    # With power loss factor
    np.testing.assert_allclose(
        actual=DirectExpressionConsumerFunction(
            fuel_rate=Expression.setup_from_expression(value="2"),
            power_loss_factor=Expression.setup_from_expression(value=0.2),
            energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.FUEL,
        )
        .evaluate(
            expression_evaluator=variables_map,
            regularity=[1.0] * variables_map.number_of_periods,
        )
        .energy_usage,
        desired=[2.5, 2.5],
    )


def test_direct_expression_consumer_function_consumption_rate_type(direct_variables_map):
    stream_day_consumption = 10.0
    regularity = 0.9
    calendar_day_consumption = f"{stream_day_consumption} {{*}} {regularity}"

    # The stream day function passes through the evaluated expression directly
    # with no modification from regularity - as this is already of "stream day" type
    stream_day_function = DirectExpressionConsumerFunction(
        load=Expression.setup_from_expression(stream_day_consumption),
        consumption_rate_type=libecalc.common.utils.rates.RateType.STREAM_DAY,
        energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.POWER,
    )
    # The calendar day function, divides the evaluated expression by regularity
    # to obtain "stream day" type as it is of "calendar day" type
    calendar_day_function = DirectExpressionConsumerFunction(
        load=Expression.setup_from_expression(calendar_day_consumption),
        consumption_rate_type=libecalc.common.utils.rates.RateType.CALENDAR_DAY,
        energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.POWER,
    )

    evaluated_regularity = [regularity] * direct_variables_map.number_of_periods

    stream_day_function_result = stream_day_function.evaluate(
        expression_evaluator=direct_variables_map,
        regularity=evaluated_regularity,
    )
    calendar_day_function_result = calendar_day_function.evaluate(
        expression_evaluator=direct_variables_map,
        regularity=evaluated_regularity,
    )

    # When regularity is used, all returned consumption values should be of stream day type
    # (as they are multiplied with regularity post calculations in the energy function)
    np.testing.assert_allclose(
        actual=calendar_day_function_result.energy_usage,
        desired=stream_day_function_result.energy_usage,
    )
