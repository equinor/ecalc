from libecalc import dto
from libecalc.core.consumers.legacy_consumer.consumer_function.direct_expression_consumer_function import (
    DirectExpressionConsumerFunction,
)


def create_direct_consumer_function(model_dto: dto.DirectConsumerFunction) -> DirectExpressionConsumerFunction:
    return DirectExpressionConsumerFunction(model_dto)
