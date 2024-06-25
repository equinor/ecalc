from typing import Generic, Literal, TypeVar

from libecalc.dto.models.energy_model import EnergyModel
from libecalc.dto.models.turbine import Turbine
from libecalc.dto.types import EnergyModelType

TCompressorTrainModel = TypeVar("TCompressorTrainModel")


class CompressorWithTurbine(EnergyModel, Generic[TCompressorTrainModel]):
    typ: Literal[EnergyModelType.COMPRESSOR_WITH_TURBINE] = EnergyModelType.COMPRESSOR_WITH_TURBINE
    compressor_train: TCompressorTrainModel
    turbine: Turbine
