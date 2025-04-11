from typing import Annotated, Union

from pydantic import Field

from libecalc.domain.process.compressor.dto import CompressorConsumerFunction
from libecalc.domain.process.pump.pump_consumer_function import PumpConsumerFunction

from .consumer_system import CompressorSystemConsumerFunction, PumpSystemConsumerFunction
from .direct import DirectConsumerFunction
from .tabulated import TabulatedConsumerFunction

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
