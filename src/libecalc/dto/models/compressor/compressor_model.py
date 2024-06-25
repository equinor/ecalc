from typing import Union

from pydantic import Field
from typing_extensions import Annotated

from libecalc.dto.models.compressor.sampled import CompressorSampled
from libecalc.dto.models.compressor.train import (
    CompressorTrainSimplifiedWithKnownStages,
    CompressorTrainSimplifiedWithUnknownStages,
    SingleSpeedCompressorTrain,
    VariableSpeedCompressorTrain,
    VariableSpeedCompressorTrainMultipleStreamsAndPressures,
)
from libecalc.dto.models.compressor.turbine import CompressorWithTurbine

CompressorModel = Annotated[
    Union[
        CompressorSampled,
        CompressorTrainSimplifiedWithUnknownStages,
        CompressorTrainSimplifiedWithKnownStages,
        VariableSpeedCompressorTrain,
        SingleSpeedCompressorTrain,
        VariableSpeedCompressorTrainMultipleStreamsAndPressures,
        CompressorWithTurbine[
            Annotated[
                Union[
                    CompressorSampled,
                    CompressorTrainSimplifiedWithUnknownStages,
                    CompressorTrainSimplifiedWithKnownStages,
                    VariableSpeedCompressorTrain,
                    SingleSpeedCompressorTrain,
                    VariableSpeedCompressorTrainMultipleStreamsAndPressures,
                ],
                Field(..., discriminator="typ"),
            ]
        ],
    ],
    Field(..., discriminator="typ"),
]

CompressorSystemModel = Annotated[
    Union[
        CompressorSampled,
        CompressorTrainSimplifiedWithUnknownStages,
        CompressorTrainSimplifiedWithKnownStages,
        VariableSpeedCompressorTrain,
        SingleSpeedCompressorTrain,
        CompressorWithTurbine[
            Annotated[
                Union[
                    CompressorSampled,
                    CompressorTrainSimplifiedWithUnknownStages,
                    CompressorTrainSimplifiedWithKnownStages,
                    VariableSpeedCompressorTrain,
                    SingleSpeedCompressorTrain,
                ],
                Field(..., discriminator="typ"),
            ]
        ],
    ],
    Field(..., discriminator="typ"),
]
