from datetime import datetime

import libecalc.common.utils.rates
import numpy as np
import pytest
from libecalc import dto
from libecalc.core.consumers.legacy_consumer.component import Consumer
from libecalc.core.consumers.legacy_consumer.consumer_function.direct_expression_consumer_function import (
    DirectExpressionConsumerFunction,
)
from libecalc.dto import VariablesMap
from libecalc.dto.base import ComponentType, ConsumerUserDefinedCategoryType
from libecalc.expression import Expression


@pytest.fixture
def direct_variables_map():
    time_vector = [datetime(2000, 1, 1), datetime(2001, 1, 1), datetime(2003, 1, 1)]
    return VariablesMap(variables={"foo;bar": [1.0] * len(time_vector)}, time_vector=time_vector)


def test_direct_expression_consumer_function():
    time_series_name = "SIM1"
    fuelratefunction = dto.DirectConsumerFunction(
        fuel_rate=Expression.setup_from_expression(time_series_name + ";Flare {+} " + time_series_name + ";Vent"),
        energy_usage_type=dto.types.EnergyUsageType.FUEL,
    )

    # Test evaluation
    variables_map = dto.VariablesMap(
        time_vector=[datetime(2000, 1, 1, 0, 0), datetime(2001, 1, 1, 0, 0)],
        variables={"SIM1;Flare": [10.0, 3.0], "SIM1;Vent": [5.0, 2.0]},
    )
    result = DirectExpressionConsumerFunction(fuelratefunction).evaluate(
        variables_map=variables_map,
        regularity=[1.0] * len(variables_map.time_vector),
    )
    expected_result = [15, 5]
    np.testing.assert_allclose(result.energy_usage, expected_result)

    # Test when used as consumer function for a fuel consumer
    fuel_consumer = Consumer(
        dto.FuelConsumer(
            name="Flare",
            component_type=ComponentType.GENERIC,
            energy_usage_model={datetime(1900, 1, 1): fuelratefunction},
            fuel={datetime(1900, 1, 1): dto.types.FuelType(name="standard_fuel", emissions=[])},
            user_defined_category={datetime(1900, 1, 1): ConsumerUserDefinedCategoryType.MISCELLANEOUS},
            regularity={datetime(1900, 1, 1): Expression.setup_from_expression(1)},
        )
    )
    result = fuel_consumer.evaluate(variables_map=variables_map)
    consumer_result = result.component_result
    np.testing.assert_allclose(
        actual=consumer_result.energy_usage.values,
        desired=expected_result,
    )

    # Test with various input to expression
    # Constant
    np.testing.assert_allclose(
        actual=DirectExpressionConsumerFunction(
            dto.DirectConsumerFunction(
                fuel_rate=Expression.setup_from_expression(value="2"), energy_usage_type=dto.types.EnergyUsageType.FUEL
            )
        )
        .evaluate(
            variables_map=variables_map,
            regularity=[1.0] * len(variables_map.time_vector),
        )
        .energy_usage,
        desired=[2, 2],
    )
    # When expression string is float even if it should be string
    np.testing.assert_allclose(
        actual=DirectExpressionConsumerFunction(
            dto.DirectConsumerFunction(
                fuel_rate=Expression.setup_from_expression(value=2.1), energy_usage_type=dto.types.EnergyUsageType.FUEL
            )
        )
        .evaluate(
            variables_map=variables_map,
            regularity=[1.0] * len(variables_map.time_vector),
        )
        .energy_usage,
        desired=[2.1, 2.1],
    )
    # Expression with numbers only
    np.testing.assert_allclose(
        actual=DirectExpressionConsumerFunction(
            dto.DirectConsumerFunction(
                fuel_rate=Expression.setup_from_expression(value="2 {+} 3.1"),
                energy_usage_type=dto.types.EnergyUsageType.FUEL,
            )
        )
        .evaluate(
            variables_map=variables_map,
            regularity=[1.0] * len(variables_map.time_vector),
        )
        .energy_usage,
        desired=[5.1, 5.1],
    )
    # Expression with time series input
    np.testing.assert_allclose(
        actual=DirectExpressionConsumerFunction(
            dto.DirectConsumerFunction(
                fuel_rate=Expression.setup_from_expression(value="0 {*} " + time_series_name + ";Flare"),
                energy_usage_type=dto.types.EnergyUsageType.FUEL,
            )
        )
        .evaluate(
            variables_map=variables_map,
            regularity=[1.0] * len(variables_map.time_vector),
        )
        .energy_usage,
        desired=[0, 0],
    )
    # Expression 0
    np.testing.assert_allclose(
        actual=DirectExpressionConsumerFunction(
            dto.DirectConsumerFunction(
                fuel_rate=Expression.setup_from_expression(value="0"), energy_usage_type=dto.types.EnergyUsageType.FUEL
            )
        )
        .evaluate(
            variables_map=variables_map,
            regularity=[1.0] * len(variables_map.time_vector),
        )
        .energy_usage,
        desired=[0, 0],
    )
    # With condition
    np.testing.assert_allclose(
        actual=DirectExpressionConsumerFunction(
            dto.DirectConsumerFunction(
                fuel_rate=Expression.setup_from_expression(value="2 {+} 3.1"),
                energy_usage_type=dto.types.EnergyUsageType.FUEL,
                condition=Expression.setup_from_expression(value="2 < 1"),
            )
        )
        .evaluate(
            variables_map=variables_map,
            regularity=[1.0] * len(variables_map.time_vector),
        )
        .energy_usage,
        desired=[0, 0],
    )
    np.testing.assert_allclose(
        actual=DirectExpressionConsumerFunction(
            dto.DirectConsumerFunction(
                fuel_rate=Expression.setup_from_expression(value="3.1"),
                energy_usage_type=dto.types.EnergyUsageType.FUEL,
                condition=Expression.multiply(
                    Expression.setup_from_expression(value="2 > 1"),
                    Expression.setup_from_expression(value=time_series_name + ";Flare > 4"),
                ),
            )
        )
        .evaluate(
            variables_map=variables_map,
            regularity=[1.0] * len(variables_map.time_vector),
        )
        .energy_usage,
        desired=[3.1, 0],
    )
    # With power loss factor
    np.testing.assert_allclose(
        actual=DirectExpressionConsumerFunction(
            dto.DirectConsumerFunction(
                fuel_rate=Expression.setup_from_expression(value="2"),
                power_loss_factor=Expression.setup_from_expression(value=0.2),
                energy_usage_type=dto.types.EnergyUsageType.FUEL,
            )
        )
        .evaluate(
            variables_map=variables_map,
            regularity=[1.0] * len(variables_map.time_vector),
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
        dto.DirectConsumerFunction(
            load=Expression.setup_from_expression(stream_day_consumption),
            consumption_rate_type=libecalc.common.utils.rates.RateType.STREAM_DAY,
            energy_usage_type=dto.types.EnergyUsageType.POWER,
        ),
    )
    # The calendar day function, divides the evaluated expression by regularity
    # to obtain "stream day" type as it is of "calendar day" type
    calendar_day_function = DirectExpressionConsumerFunction(
        dto.DirectConsumerFunction(
            load=Expression.setup_from_expression(calendar_day_consumption),
            consumption_rate_type=libecalc.common.utils.rates.RateType.CALENDAR_DAY,
            energy_usage_type=dto.types.EnergyUsageType.POWER,
        )
    )

    evaluated_regularity = [regularity] * len(direct_variables_map.time_vector)

    stream_day_function_result = stream_day_function.evaluate(
        variables_map=direct_variables_map,
        regularity=evaluated_regularity,
    )
    calendar_day_function_result = calendar_day_function.evaluate(
        variables_map=direct_variables_map,
        regularity=evaluated_regularity,
    )

    # When regularity is used, all returned consumption values should be of stream day type
    # (as they are multiplied with regularity post calculations in the energy function)
    np.testing.assert_allclose(
        actual=calendar_day_function_result.energy_usage,
        desired=stream_day_function_result.energy_usage,
    )
