import pytest

from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.utils.rates import RateType
from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function.direct_expression_consumer_function import (
    DirectExpressionConsumerFunction,
)
from libecalc.expression import Expression


@pytest.fixture
def direct_expression_model_factory():
    def create_direct_expression_model(
        expression: Expression,
        energy_usage_type: EnergyUsageType,
        consumption_rate_type: RateType = RateType.STREAM_DAY,
    ):
        if energy_usage_type == EnergyUsageType.POWER:
            return DirectExpressionConsumerFunction(
                energy_usage_type=energy_usage_type,
                load=expression,
                power_loss_factor=None,
                consumption_rate_type=consumption_rate_type,
            )
        else:
            return DirectExpressionConsumerFunction(
                energy_usage_type=energy_usage_type,
                fuel_rate=expression,
                power_loss_factor=None,
                consumption_rate_type=consumption_rate_type,
            )

    return create_direct_expression_model
