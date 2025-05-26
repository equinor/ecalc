from typing import Union

from libecalc.common.energy_model_type import EnergyModelType
from libecalc.domain.infrastructure.energy_components.generator_set import GeneratorSetModel
from libecalc.domain.process.compressor.dto import CompressorSampled as CompressorTrainSampledDTO
from libecalc.domain.process.dto import TabulatedData

EnergyModelUnionType = Union[GeneratorSetModel, TabulatedData, CompressorTrainSampledDTO]


class EnergyModelFactory:
    """
    The EnergyModelFactory class is designed to create instances of various energy model types.
    It provides a static method `create` that takes an `EnergyModelType` and a dictionary of model data,
    and returns an instance of the corresponding energy model class. This factory pattern ensures that
    the correct energy model is instantiated based on the provided type, facilitating the conversion
    of facility data into appropriate DTO models. Supported energy model types include `GeneratorSetSampled`,
    `TabulatedData`, and `CompressorTrainSampledDTO`. If an unsupported `EnergyModelType` is provided,
    a `ValueError` is raised.
    """

    @staticmethod
    def create(typ: EnergyModelType, model_data: dict) -> EnergyModelUnionType:
        model_data = {key: value for key, value in model_data.items() if key != "typ"}

        if typ == EnergyModelType.GENERATOR_SET_SAMPLED:
            # Ensure 'name' is present in model_data, with a default value if missing
            model_data.setdefault("name", "generator_set_sampled_default_name")
            return GeneratorSetModel(**model_data)
        elif typ == EnergyModelType.TABULATED:
            return TabulatedData(**model_data)
        elif typ == EnergyModelType.COMPRESSOR_SAMPLED:
            return CompressorTrainSampledDTO(**model_data)
        else:
            raise ValueError(f"Unsupported EnergyModelType: {typ}")
