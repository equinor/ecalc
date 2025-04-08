from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function.direct_expression_consumer_function import (
    DirectExpressionConsumerFunction,
)
from libecalc.domain.process.dto import DirectConsumerFunction


def create_direct_consumer_function(model_dto: DirectConsumerFunction) -> DirectExpressionConsumerFunction:
    return DirectExpressionConsumerFunction(
        energy_usage_type=model_dto.energy_usage_type,
        condition=model_dto.condition,
        fuel_rate=model_dto.fuel_rate,
        load=model_dto.load,
        power_loss_factor=model_dto.power_loss_factor,
        consumption_rate_type=model_dto.consumption_rate_type,
    )
