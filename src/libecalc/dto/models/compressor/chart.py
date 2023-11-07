from typing import Union

from pydantic import Field
from typing_extensions import Annotated

from libecalc.dto.models.chart import (
    GenericChartFromDesignPoint,
    GenericChartFromInput,
    SingleSpeedChart,
    VariableSpeedChart,
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
