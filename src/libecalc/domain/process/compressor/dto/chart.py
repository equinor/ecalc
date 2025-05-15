from typing import Annotated, Union

from pydantic import Field

from libecalc.domain.process.core.chart import SingleSpeedChart, VariableSpeedChart
from libecalc.domain.process.dto.chart import (
    GenericChartFromDesignPoint,
    GenericChartFromInput,
)

CompressorChart = Annotated[
    Union[
        GenericChartFromInput,
        GenericChartFromDesignPoint,
        VariableSpeedChart,
        SingleSpeedChart,
    ],
    Field(discriminator="typ"),
]
