from typing import Any, Dict, List, Literal, Optional

import numpy as np
from libecalc.common.logger import logger
from libecalc.common.numbers import Numbers
from libecalc.dto.base import EcalcBaseModel
from libecalc.dto.types import ChartType
from pydantic import Field, confloat, root_validator, validator


class ChartCurve(EcalcBaseModel):
    speed_rpm: float = Field(..., ge=0)
    rate_actual_m3_hour: List[confloat(ge=0)]  # type: ignore
    polytropic_head_joule_per_kg: List[confloat(ge=0)]  # type: ignore
    efficiency_fraction: List[confloat(ge=0, le=1)]  # type: ignore

    @validator("*", pre=True, each_item=True)
    def control_maximum_decimals(cls, v: float) -> float:
        """Control maximum number of decimals and convert null-floats to NaN."""
        if isinstance(v, float):
            if v.is_integer():
                return v

            return float(Numbers.format_to_precision(v, precision=6))

        return v

    @root_validator(skip_on_failure=True)
    def validate_equal_lengths_and_sort(cls, v: Dict[str, Any]) -> Any:
        rate = v["rate_actual_m3_hour"]
        head = v["polytropic_head_joule_per_kg"]
        efficiency = v["efficiency_fraction"]

        if not len(rate) == len(head) == len(efficiency):
            raise ValueError("All chart curve data must have equal number of points")

        if not len(rate) > 1:
            raise ValueError("A chart curve can not be defined by a single point. At least two points must be given.")

        # Sort all values by rate
        array = np.asarray([rate, head, efficiency]).T
        array_sorted = array[array[:, 0].argsort()]

        v["rate_actual_m3_hour"] = list(array_sorted[:, 0])
        v["polytropic_head_joule_per_kg"] = list(array_sorted[:, 1])
        v["efficiency_fraction"] = list(array_sorted[:, 2])

        if len(set(v["rate_actual_m3_hour"])) != len(v["rate_actual_m3_hour"]):
            duplicate_rates = {x for x in v["rate_actual_m3_hour"] if v["rate_actual_m3_hour"].count(x) > 1}
            logger.warning(f"Duplicate rate values in ChartCurve: {duplicate_rates}")

        if not np.all(np.diff(np.asarray(v["polytropic_head_joule_per_kg"])) <= 0):
            heads = v["polytropic_head_joule_per_kg"]
            rates = v["rate_actual_m3_hour"]
            logger.warning(
                "Head is increasing with rate in a ChartCurve."
                " Interpolations are based on the assumption of an inverse monotonic function between head and rate."
                f" Given head values: {heads}"
                f" Given rate values: {rates}"
            )

        return v

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


class SingleSpeedChart(ChartCurve):
    typ: Literal[ChartType.SINGLE_SPEED] = ChartType.SINGLE_SPEED


class VariableSpeedChart(EcalcBaseModel):
    typ: Literal[ChartType.VARIABLE_SPEED] = ChartType.VARIABLE_SPEED
    curves: List[ChartCurve]
    control_margin: Optional[float]  # Todo: Raise warning if this is used in an un-supported model.
    design_rate: Optional[float] = Field(None, ge=0)
    design_head: Optional[float] = Field(None, ge=0)

    @validator("*", pre=True, each_item=True)
    def control_maximum_decimals(cls, v: float) -> float:
        """Control maximum number of decimals and convert null-floats to NaN."""
        if isinstance(v, float):
            if v.is_integer():
                return v

            return float(Numbers.format_to_precision(v, precision=6))

        return v

    @validator("curves", pre=False)
    def sort_chart_curves_by_speed(cls, curves: List[ChartCurve]) -> List[ChartCurve]:
        """Note: It is essential that the sort the curves by speed in order to set up the interpolations correctly."""
        return sorted(curves, key=lambda x: x.speed)

    @property
    def min_speed(self) -> float:
        return min([curve.speed for curve in self.curves])

    @property
    def max_speed(self) -> float:
        return max([curve.speed for curve in self.curves])


class GenericChartFromDesignPoint(EcalcBaseModel):
    typ: Literal[ChartType.GENERIC_FROM_DESIGN_POINT.value] = ChartType.GENERIC_FROM_DESIGN_POINT
    polytropic_efficiency_fraction: float = Field(..., ge=0, le=1)
    design_rate_actual_m3_per_hour: float = Field(..., ge=0)
    design_polytropic_head_J_per_kg: float = Field(..., ge=0)


class GenericChartFromInput(EcalcBaseModel):
    typ: Literal[ChartType.GENERIC_FROM_INPUT] = ChartType.GENERIC_FROM_INPUT
    polytropic_efficiency_fraction: float = Field(..., ge=0, le=1)
