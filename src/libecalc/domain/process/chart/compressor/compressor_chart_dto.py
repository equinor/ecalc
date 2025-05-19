from typing import Annotated, Union

from pydantic import Field

from libecalc.common.serializable_chart import SingleSpeedChartDTO, VariableSpeedChartDTO
from libecalc.domain.process.chart.generic.chart import (
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
