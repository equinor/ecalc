from typing import List, Literal, Optional

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from typing_extensions import Annotated, Self

from libecalc.common.chart_type import ChartType
from libecalc.common.logger import logger
from libecalc.common.string.string_utils import to_camel_case


class EcalcBaseModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        alias_generator=to_camel_case,
        populate_by_name=True,
    )


class ChartCurveDTO(EcalcBaseModel):
    speed_rpm: float = Field(..., ge=0)
    rate_actual_m3_hour: List[Annotated[float, Field(ge=0)]]
    polytropic_head_joule_per_kg: List[Annotated[float, Field(ge=0)]]
    efficiency_fraction: List[Annotated[float, Field(gt=0, le=1)]]

    @model_validator(mode="after")
    def validate_equal_lengths_and_sort(self) -> Self:
        rate = self.rate_actual_m3_hour
        head = self.polytropic_head_joule_per_kg
        efficiency = self.efficiency_fraction

        if not len(rate) == len(head) == len(efficiency):
            raise ValueError("All chart curve data must have equal number of points")

        if not len(rate) > 1:
            raise ValueError("A chart curve can not be defined by a single point. At least two points must be given.")

        # Sort all values by rate
        array = np.asarray([rate, head, efficiency]).T
        array_sorted = array[array[:, 0].argsort()]

        self.rate_actual_m3_hour = list(array_sorted[:, 0])
        self.polytropic_head_joule_per_kg = list(array_sorted[:, 1])
        self.efficiency_fraction = list(array_sorted[:, 2])

        if len(set(self.rate_actual_m3_hour)) != len(self.rate_actual_m3_hour):
            duplicate_rates = {x for x in self.rate_actual_m3_hour if self.rate_actual_m3_hour.count(x) > 1}
            logger.warning(f"Duplicate rate values in ChartCurve: {duplicate_rates}")

        if not np.all(np.diff(np.asarray(self.polytropic_head_joule_per_kg)) <= 0):
            heads = self.polytropic_head_joule_per_kg
            rates = self.rate_actual_m3_hour
            logger.warning(
                "Head is increasing with rate in a ChartCurve."
                " Interpolations are based on the assumption of an inverse monotonic function between head and rate."
                f" Given head values: {heads}"
                f" Given rate values: {rates}"
            )

        return self

    @property
    def rate(self) -> List[float]:
        return self.rate_actual_m3_hour

    @property
    def head(self) -> List[float]:
        return self.polytropic_head_joule_per_kg

    @property
    def efficiency(self) -> List[float]:
        return self.efficiency_fraction

    @property
    def speed(self) -> float:
        return self.speed_rpm


class SingleSpeedChartDTO(ChartCurveDTO):
    typ: Literal[ChartType.SINGLE_SPEED] = ChartType.SINGLE_SPEED


class VariableSpeedChartDTO(EcalcBaseModel):
    typ: Literal[ChartType.VARIABLE_SPEED] = ChartType.VARIABLE_SPEED
    curves: List[ChartCurveDTO]
    control_margin: Optional[float] = None  # Todo: Raise warning if this is used in an un-supported model.
    design_rate: Optional[float] = Field(None, ge=0)
    design_head: Optional[float] = Field(None, ge=0)

    @field_validator("curves")
    def sort_chart_curves_by_speed(cls, curves: List[ChartCurveDTO]) -> List[ChartCurveDTO]:
        """Note: It is essential that the sort the curves by speed in order to set up the interpolations correctly."""
        return sorted(curves, key=lambda x: x.speed)

    @property
    def min_speed(self) -> float:
        return min([curve.speed for curve in self.curves])

    @property
    def max_speed(self) -> float:
        return max([curve.speed for curve in self.curves])
