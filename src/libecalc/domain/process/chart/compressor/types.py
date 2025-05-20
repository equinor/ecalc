from libecalc.domain.process.chart.chart_area_flag import ChartAreaFlag


class CompressorChartHeadEfficiencyResultSinglePoint:
    def __init__(
        self, polytropic_head: float, polytropic_efficiency: float, chart_area_flag: ChartAreaFlag, is_valid: bool
    ):
        self.polytropic_head = polytropic_head
        self.polytropic_efficiency = polytropic_efficiency
        self.chart_area_flag = chart_area_flag
        self.is_valid = is_valid


class CompressorChartResult:
    """asv_corrected_rates: Rates [Am3/h] corrected for Anti Surge Valve.
    choke_corrected_heads: Heads [J/kg] when corrected for Choke
    rate_has_recirc: Rate [Am3/h] when recirculating
    pressure_is_choked: True or False
    rate_exceeds_maximum: True or False
    head_exceeds_maximum: True or False
    exceeds_capacity:
    """

    def __init__(
        self,
        asv_corrected_rates: list[float],
        choke_corrected_heads: list[float],
        rate_has_recirc: list[bool],
        pressure_is_choked: list[bool],
        rate_exceeds_maximum: list[bool],
        head_exceeds_maximum: list[bool],
        exceeds_capacity: list[bool],
    ):
        self.asv_corrected_rates = asv_corrected_rates
        self.choke_corrected_heads = choke_corrected_heads
        self.rate_has_recirc = rate_has_recirc
        self.pressure_is_choked = pressure_is_choked
        self.rate_exceeds_maximum = rate_exceeds_maximum
        self.head_exceeds_maximum = head_exceeds_maximum
        self.exceeds_capacity = exceeds_capacity

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
