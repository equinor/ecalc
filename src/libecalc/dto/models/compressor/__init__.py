from typing import Union

from .base import (
    CompressorConsumerFunction,
    CompressorInSystemModel,
    CompressorModel,
    CompressorWithTurbine,
)
from .chart import CompressorChart
from .fluid import (
    FluidComposition,
    FluidModel,
    FluidStream,
    MultipleStreamsAndPressureStream,
)
from .sampled import CompressorSampled
from .stage import (
    CompressorStage,
    InterstagePressureControl,
    MultipleStreamsCompressorStage,
)
from .train import (
    CompressorTrainSimplifiedWithKnownStages,
    CompressorTrainSimplifiedWithUnknownStages,
    SingleSpeedCompressorTrain,
    VariableSpeedCompressorTrain,
    VariableSpeedCompressorTrainMultipleStreamsAndPressures,
)
