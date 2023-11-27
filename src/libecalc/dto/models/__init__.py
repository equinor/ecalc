from typing import Union

from libecalc.dto.models.compressor import (
    CompressorChart,
    CompressorConsumerFunction,
    CompressorModel,
    CompressorSampled,
    CompressorStage,
    CompressorTrainSimplifiedWithKnownStages,
    CompressorTrainSimplifiedWithUnknownStages,
    CompressorWithTurbine,
    FluidComposition,
    FluidModel,
    FluidStream,
    InterstagePressureControl,
    MultipleStreamsAndPressureStream,
    MultipleStreamsCompressorStage,
    SingleSpeedCompressorTrain,
    VariableSpeedCompressorTrain,
    VariableSpeedCompressorTrainMultipleStreamsAndPressures,
)

from .base import ConsumerFunction, EnergyModel
from .chart import (
    ChartCurve,
    GenericChartFromDesignPoint,
    GenericChartFromInput,
    SingleSpeedChart,
    VariableSpeedChart,
)
from .consumer_system import (
    CompressorSystemCompressor,
    CompressorSystemConsumerFunction,
    CompressorSystemOperationalSetting,
    PumpSystemConsumerFunction,
    PumpSystemOperationalSetting,
    PumpSystemPump,
    SystemOperationalSetting,
)
from .direct import DirectConsumerFunction
from .generator_set import GeneratorSetSampled
from .pump import PumpConsumerFunction, PumpModel
from .sampled import EnergyModelSampled
from .tabulated import TabulatedConsumerFunction, TabulatedData, Variables
from .turbine import Turbine

ElectricEnergyUsageModel = Union[
    DirectConsumerFunction,
    CompressorConsumerFunction,
    CompressorSystemConsumerFunction,
    PumpConsumerFunction,
    TabulatedConsumerFunction,
    PumpSystemConsumerFunction,
]

FuelEnergyUsageModel = Union[
    DirectConsumerFunction,
    CompressorConsumerFunction,
    CompressorSystemConsumerFunction,
    TabulatedConsumerFunction,
]

EnergyUsageModel = Union[
    FuelEnergyUsageModel,
    ElectricEnergyUsageModel,
]
