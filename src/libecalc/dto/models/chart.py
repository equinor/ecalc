from typing import Literal

from pydantic import Field

from libecalc.common.chart_type import ChartType
from libecalc.dto.base import EcalcBaseModel


class GenericChartFromDesignPoint(EcalcBaseModel):
    typ: Literal[ChartType.GENERIC_FROM_DESIGN_POINT] = ChartType.GENERIC_FROM_DESIGN_POINT
    polytropic_efficiency_fraction: float = Field(..., gt=0, le=1)
    design_rate_actual_m3_per_hour: float = Field(..., ge=0)
    design_polytropic_head_J_per_kg: float = Field(..., ge=0)


class GenericChartFromInput(EcalcBaseModel):
    typ: Literal[ChartType.GENERIC_FROM_INPUT] = ChartType.GENERIC_FROM_INPUT
    polytropic_efficiency_fraction: float = Field(..., gt=0, le=1)
