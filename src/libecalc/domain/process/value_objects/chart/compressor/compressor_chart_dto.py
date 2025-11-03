from typing import Annotated, Union

from pydantic import Field

from libecalc.domain.process.value_objects.chart.chart import ChartData
from libecalc.domain.process.value_objects.chart.generic.chart import GenericChartFromDesignPoint, GenericChartFromInput

CompressorChartDTO = Annotated[
    Union[
        GenericChartFromInput,
        GenericChartFromDesignPoint,
        ChartData,
    ],
    Field(discriminator="typ"),
]
