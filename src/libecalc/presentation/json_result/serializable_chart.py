from typing import Annotated, Self

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator

from libecalc.common.logger import logger
from libecalc.common.string.string_utils import to_camel_case
from libecalc.domain.process.value_objects.chart.base import ChartCurve
from libecalc.domain.process.value_objects.chart.chart import ChartData
from libecalc.presentation.yaml.mappers.charts.generic_from_design_point_chart_data import (
    GenericFromDesignPointChartData,
)
from libecalc.presentation.yaml.mappers.charts.generic_from_input_chart_data import GenericFromInputChartData
from libecalc.presentation.yaml.mappers.charts.user_defined_chart_data import UserDefinedChartData


class EcalcBaseModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        alias_generator=to_camel_case,
        populate_by_name=True,
    )


class OperationalPointDTO(EcalcBaseModel):
    rate_actual_m3_hour: Annotated[float, Field(ge=0)]
    polytropic_head_joule_per_kg: Annotated[float, Field(ge=0)]
    efficiency_fraction: Annotated[float, Field(gt=0, le=1)]


class ChartCurveDTO(EcalcBaseModel):
    speed_rpm: float = Field(..., ge=0)
    rate_actual_m3_hour: list[Annotated[float, Field(ge=0)]]
    polytropic_head_joule_per_kg: list[Annotated[float, Field(ge=0)]]
    efficiency_fraction: list[Annotated[float, Field(gt=0, le=1)]]

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
    def rate(self) -> list[float]:
        return self.rate_actual_m3_hour

    @property
    def head(self) -> list[float]:
        return self.polytropic_head_joule_per_kg

    @property
    def efficiency(self) -> list[float]:
        return self.efficiency_fraction

    @property
    def speed(self) -> float:
        return self.speed_rpm

    @classmethod
    def from_domain(cls, chart_curve: ChartCurve) -> Self:
        return ChartCurveDTO(
            speed_rpm=chart_curve.speed,
            rate_actual_m3_hour=chart_curve.rate,
            polytropic_head_joule_per_kg=chart_curve.head,
            efficiency_fraction=chart_curve.efficiency,
        )


class ChartDTO(EcalcBaseModel):
    curves: list[ChartCurveDTO]
    control_margin_line: list[OperationalPointDTO] | None = None
    control_margin: float | None = None
    design_rate: float | None = Field(None, ge=0)
    design_head: float | None = Field(None, ge=0)

    @classmethod
    def from_domain(cls, chart: ChartData) -> Self:
        design_rate: float | None = None
        design_head: float | None = None
        if isinstance(chart, GenericFromDesignPointChartData | GenericFromInputChartData):
            design_head = chart.design_head
            design_rate = chart.design_rate

        control_margin: float | None = None
        control_margin_line: list[OperationalPointDTO] = []
        if isinstance(chart, UserDefinedChartData):
            control_margin = chart.control_margin

            if control_margin is not None and control_margin > 0:
                adjusted_curves = chart.get_adjusted_curves()
                for curve in adjusted_curves:
                    control_margin_line.append(
                        OperationalPointDTO(
                            rate_actual_m3_hour=curve.rate_actual_m3_hour[0],
                            polytropic_head_joule_per_kg=curve.polytropic_head_joule_per_kg[0],
                            efficiency_fraction=curve.efficiency_fraction[0],
                        )
                    )

        return ChartDTO(
            curves=[ChartCurveDTO.from_domain(chart_curve=curve) for curve in chart.get_original_curves()],
            design_rate=design_rate,
            design_head=design_head,
            control_margin=control_margin,
            control_margin_line=control_margin_line if control_margin_line else None,
        )
