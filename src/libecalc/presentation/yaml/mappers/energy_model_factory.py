from typing import Union

from libecalc.common.energy_model_type import EnergyModelType
from libecalc.domain.process.dto import CompressorSampled as CompressorTrainSampledDTO
from libecalc.domain.process.dto import GeneratorSetSampled, TabulatedData

EnergyModelUnionType = Union[GeneratorSetSampled, TabulatedData, CompressorTrainSampledDTO]


class EnergyModelFactory:
    @staticmethod
    def create(typ: EnergyModelType, model_data: dict) -> EnergyModelUnionType:
        model_data = {key: value for key, value in model_data.items() if key != "typ"}

        if typ == EnergyModelType.GENERATOR_SET_SAMPLED:
            return GeneratorSetSampled(**model_data)
        elif typ == EnergyModelType.TABULATED:
            return TabulatedData(**model_data)
        elif typ == EnergyModelType.COMPRESSOR_SAMPLED:
            return CompressorTrainSampledDTO(**model_data)
        else:
            raise ValueError(f"Unsupported EnergyModelType: {typ}")
