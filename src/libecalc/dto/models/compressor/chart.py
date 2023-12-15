from typing import Union

try:
    from pydantic.v1 import Field
except ImportError:
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
