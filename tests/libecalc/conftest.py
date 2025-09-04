import pytest

from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.utils.rates import RateType
from libecalc.common.variables import ExpressionEvaluator
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function.direct_consumer_function import (
    DirectConsumerFunction,
)
from libecalc.domain.regularity import Regularity
from libecalc.expression.expression import ExpressionType
from libecalc.presentation.yaml.domain.expression_time_series_flow_rate import ExpressionTimeSeriesFlowRate
from libecalc.presentation.yaml.domain.expression_time_series_power import ExpressionTimeSeriesPower
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


@pytest.fixture
def regularity_factory():
    def create_regularity(expression_evaluator: ExpressionEvaluator, regularity_value: ExpressionType = 1):
        regularity = Regularity(
            expression_input=regularity_value,
            expression_evaluator=expression_evaluator,
            target_period=expression_evaluator.get_period(),
        )
        return regularity

    return create_regularity


@pytest.fixture
def direct_expression_model_factory(regularity_factory):
    def create_direct_expression_model(
        expression: ExpressionType,
        energy_usage_type: EnergyUsageType,
        expression_evaluator: ExpressionEvaluator,
        consumption_rate_type: RateType = RateType.STREAM_DAY,
        regularity: Regularity | None = None,
    ):
        if regularity is None:
            regularity = regularity_factory(expression_evaluator)

        usage_expression = TimeSeriesExpression(expression=expression, expression_evaluator=expression_evaluator)
        usage_power = ExpressionTimeSeriesPower(
            time_series_expression=usage_expression, regularity=regularity, consumption_rate_type=consumption_rate_type
        )
        usage_fuel = ExpressionTimeSeriesFlowRate(
            time_series_expression=usage_expression, regularity=regularity, consumption_rate_type=consumption_rate_type
        )

        if energy_usage_type == EnergyUsageType.POWER:
            return DirectConsumerFunction(
                energy_usage_type=energy_usage_type,
                load=usage_power,
                power_loss_factor=None,
            )
        else:
            return DirectConsumerFunction(
                energy_usage_type=energy_usage_type,
                fuel_rate=usage_fuel,
                power_loss_factor=None,
            )

    return create_direct_expression_model
