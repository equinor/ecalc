from typing import Union

from libecalc.dto.models.chart import (
    GenericChartFromDesignPoint,
    GenericChartFromInput,
    SingleSpeedChart,
    VariableSpeedChart,
)
from pydantic import Field
from typing_extensions import Annotated

CompressorChart = Annotated[
    Union[
        GenericChartFromInput,
        GenericChartFromDesignPoint,
        VariableSpeedChart,
        SingleSpeedChart,
    ],
    Field(discriminator="typ"),
]
