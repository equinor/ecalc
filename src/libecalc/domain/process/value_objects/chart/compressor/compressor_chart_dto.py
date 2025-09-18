from typing import Annotated, Union

from pydantic import Field

from libecalc.common.serializable_chart import ChartDTO
from libecalc.domain.process.value_objects.chart.generic.chart import GenericChartFromDesignPoint, GenericChartFromInput

CompressorChartDTO = Annotated[
    Union[
        GenericChartFromInput,
        GenericChartFromDesignPoint,
        ChartDTO,
    ],
    Field(discriminator="typ"),
]
