"""
Compressor model types and building blocks for unions and direct usage.
Used across core logic, factories, and consumer function typing.
"""

from typing import Union

from .sampled import CompressorSampled
from .train import (
    CompressorTrainSimplifiedWithKnownStages,
    CompressorTrainSimplifiedWithUnknownStages,
    SingleSpeedCompressorTrain,
    VariableSpeedCompressorTrain,
    VariableSpeedCompressorTrainMultipleStreamsAndPressures,
)
from .with_turbine import CompressorWithTurbine

CompressorModelTypes = Union[
    CompressorSampled,
    CompressorTrainSimplifiedWithUnknownStages,
    CompressorTrainSimplifiedWithKnownStages,
    CompressorWithTurbine,
    VariableSpeedCompressorTrain,
    SingleSpeedCompressorTrain,
    VariableSpeedCompressorTrainMultipleStreamsAndPressures,
]
