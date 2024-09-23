from typing import Union

from pydantic import Field
from typing_extensions import Annotated

from libecalc.dto.models.chart import (
    GenericChartFromDesignPoint,
    GenericChartFromInput,
    SingleSpeedChartDTO,
    VariableSpeedChartDTO,
)

CompressorChart = Annotated[
    Union[
        GenericChartFromInput,
        GenericChartFromDesignPoint,
        VariableSpeedChartDTO,
        SingleSpeedChartDTO,
    ],
    Field(discriminator="typ"),
]
