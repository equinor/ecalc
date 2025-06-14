from libecalc.domain.infrastructure.energy_components.legacy_consumer.consumer_function.compressor_consumer_function import (
    CompressorConsumerFunction,
)
from libecalc.domain.process.compressor.core import create_compressor_model
from libecalc.domain.process.compressor.dto import CompressorConsumerFunction as CompressorConsumerFunctionDTO


def create_compressor_consumer_function(model_dto: CompressorConsumerFunctionDTO) -> CompressorConsumerFunction:
    compressor_model = create_compressor_model(compressor_model_dto=model_dto.model)
    return CompressorConsumerFunction(
        condition_expression=model_dto.condition,  # type: ignore[arg-type]
        power_loss_factor_expression=model_dto.power_loss_factor,  # type: ignore[arg-type]
        compressor_function=compressor_model,
        rate_expression=model_dto.rate_standard_m3_day,  # type: ignore[arg-type]
        suction_pressure_expression=model_dto.suction_pressure,  # type: ignore[arg-type]
        discharge_pressure_expression=model_dto.discharge_pressure,  # type: ignore[arg-type]
        intermediate_pressure_expression=model_dto.interstage_control_pressure,  # type: ignore[arg-type]
    )
