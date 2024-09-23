from typing import Union

from pydantic import Field
from typing_extensions import Annotated

from libecalc.common.serializable_chart import SingleSpeedChartDTO, VariableSpeedChartDTO
from libecalc.dto.models.chart import (
    GenericChartFromDesignPoint,
    GenericChartFromInput,
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
