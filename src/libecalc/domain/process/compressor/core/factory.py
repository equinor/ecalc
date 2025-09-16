from libecalc.domain.process.compressor.core.sampled import CompressorModelSampled
from libecalc.domain.process.compressor.dto import (
    CompressorSampled,
)


def _create_compressor_sampled(compressor_model_dto: CompressorSampled) -> CompressorModelSampled:
    return CompressorModelSampled(
        energy_usage_adjustment_constant=compressor_model_dto.energy_usage_adjustment_constant,
        energy_usage_adjustment_factor=compressor_model_dto.energy_usage_adjustment_factor,
        energy_usage_type=compressor_model_dto.energy_usage_type,
        energy_usage_values=compressor_model_dto.energy_usage_values,
        rate_values=compressor_model_dto.rate_values,
        suction_pressure_values=compressor_model_dto.suction_pressure_values,
        discharge_pressure_values=compressor_model_dto.discharge_pressure_values,
        power_interpolation_values=compressor_model_dto.power_interpolation_values,
    )
