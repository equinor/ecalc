from libecalc import dto
from libecalc.core.consumers.legacy_consumer.consumer_function.compressor_consumer_function import (
    CompressorConsumerFunction,
)
from libecalc.core.models.compressor import create_compressor_model


def create_compressor_consumer_function(model_dto: dto.CompressorConsumerFunction) -> CompressorConsumerFunction:
    compressor_model = create_compressor_model(compressor_model_dto=model_dto.model)
    return CompressorConsumerFunction(
        condition_expression=model_dto.condition,
        power_loss_factor_expression=model_dto.power_loss_factor,
        compressor_function=compressor_model,
        rate_expression=model_dto.rate_standard_m3_day,
        suction_pressure_expression=model_dto.suction_pressure,
        discharge_pressure_expression=model_dto.discharge_pressure,
        intermediate_pressure_expression=model_dto.interstage_control_pressure,
    )
