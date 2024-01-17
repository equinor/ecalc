from typing import Union

from pydantic import Field
from typing_extensions import Annotated

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

ElectricEnergyUsageModel = Annotated[
    Union[
        DirectConsumerFunction,
        CompressorConsumerFunction,
        CompressorSystemConsumerFunction,
        PumpConsumerFunction,
        TabulatedConsumerFunction,
        PumpSystemConsumerFunction,
    ],
    Field(discriminator="typ"),
]

FuelEnergyUsageModel = Annotated[
    Union[
        DirectConsumerFunction,
        CompressorConsumerFunction,
        CompressorSystemConsumerFunction,
        TabulatedConsumerFunction,
    ],
    Field(discriminator="typ"),
]

EnergyUsageModel = Annotated[
    Union[
        FuelEnergyUsageModel,
        ElectricEnergyUsageModel,
    ],
    Field(discriminator="typ"),
]
