from libecalc.core.consumers.legacy_consumer.consumer_function.direct_expression_consumer_function import (
    DirectExpressionConsumerFunction,
)
from libecalc.dto import DirectConsumerFunction


def create_direct_consumer_function(model_dto: DirectConsumerFunction) -> DirectExpressionConsumerFunction:
    return DirectExpressionConsumerFunction(model_dto)
