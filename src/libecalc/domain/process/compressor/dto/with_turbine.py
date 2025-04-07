from typing import Literal

from libecalc.common.energy_model_type import EnergyModelType
from libecalc.domain.process.compressor.dto.sampled import CompressorSampled
from libecalc.domain.process.compressor.dto.train import (
    CompressorTrainSimplifiedWithKnownStages,
    CompressorTrainSimplifiedWithUnknownStages,
    SingleSpeedCompressorTrain,
    VariableSpeedCompressorTrain,
    VariableSpeedCompressorTrainMultipleStreamsAndPressures,
)
from libecalc.domain.process.dto.base import EnergyModel
from libecalc.domain.process.dto.turbine import Turbine


class CompressorWithTurbine(EnergyModel):
    typ: Literal[EnergyModelType.COMPRESSOR_WITH_TURBINE] = EnergyModelType.COMPRESSOR_WITH_TURBINE

    def __init__(
        self,
        energy_usage_adjustment_constant: float,
        energy_usage_adjustment_factor: float,
        compressor_train: (
            CompressorSampled
            | CompressorTrainSimplifiedWithKnownStages
            | CompressorTrainSimplifiedWithUnknownStages
            | SingleSpeedCompressorTrain
            | VariableSpeedCompressorTrain
            | VariableSpeedCompressorTrainMultipleStreamsAndPressures
        ),
        turbine: Turbine,
    ):
        super().__init__(energy_usage_adjustment_constant, energy_usage_adjustment_factor)
        self.compressor_train = compressor_train
        self.turbine = turbine
