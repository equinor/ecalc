from pydantic import BaseModel, ConfigDict

from libecalc.core.models.chart.chart_area_flag import ChartAreaFlag


class CompressorChartHeadEfficiencyResultSinglePoint(BaseModel):
    polytropic_head: float
    polytropic_efficiency: float
    chart_area_flag: ChartAreaFlag
    is_valid: bool


class CompressorChartResult(BaseModel):
    """asv_corrected_rates: Rates [Am3/h] corrected for Anti Surge Valve.
    choke_corrected_heads: Heads [J/kg] when corrected for Choke
    rate_has_recirc: Rate [Am3/h] when recirculating
    pressure_is_choked: True or False
    rate_exceeds_maximum: True or False
    head_exceeds_maximum: True or False
    exceeds_capacity:
    """

    asv_corrected_rates: list[float]
    choke_corrected_heads: list[float]
    rate_has_recirc: list[bool]
    pressure_is_choked: list[bool]
    rate_exceeds_maximum: list[bool]
    head_exceeds_maximum: list[bool]
    exceeds_capacity: list[bool]
    model_config = ConfigDict(extra="forbid")

    @property
    def any_points_below_stone_wall(self):
        return any(
            rate_exceeds_maximum and not_head_exceeds_maximum
            for (rate_exceeds_maximum, not_head_exceeds_maximum) in zip(
                self.rate_exceeds_maximum,
                [not head_exceeds_maximum for head_exceeds_maximum in self.head_exceeds_maximum],
            )
        )

    @property
    def any_points_above_maximum_speed_curve(self):
        return any(
            rate_exceeds_maximum and head_exceeds_maximum
            for (rate_exceeds_maximum, head_exceeds_maximum) in zip(
                self.rate_exceeds_maximum, self.head_exceeds_maximum
            )
        )
