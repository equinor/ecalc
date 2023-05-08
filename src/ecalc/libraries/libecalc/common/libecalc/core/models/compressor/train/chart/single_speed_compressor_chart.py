from typing import Tuple

from libecalc.core.models.chart import SingleSpeedChart
from libecalc.core.models.compressor.train.chart.types import (
    CompressorChartHeadEfficiencyResultSinglePoint,
)
from libecalc.dto.types import ChartAreaFlag


class SingleSpeedCompressorChart(SingleSpeedChart):
    """A user specified compressor chart given in actual volume rate [Am3/h] versus head [J/kg].

    Note: head often denoted in mlc/m or kJ/kg in vendor data. Input here is J/kg (not kJ/kg) as this is used for
    calculations and must be converted to J/kg before using this class
    Chart may be used with or without efficiency values.
    """

    def _evaluate_point_validity_chart_area_flag_and_adjusted_rate(
        self,
        rate: float,
        recirculated_rate: float,
        increase_rate_left_of_minimum_flow_assuming_asv: bool,
    ) -> Tuple[bool, ChartAreaFlag, float]:
        """:param rate: [Am3/h] initial rate to set correct chart area flag
        :param recirculated_rate: [Am3/h] rate added by asv (individual or common)
        :param increase_rate_left_of_minimum_flow_assuming_asv: True or False.
        :return:
        """
        chart_area_flag = self.get_chart_area_flag(rate=rate)
        rate_corrected_to_minimum_flow = (
            max(rate + recirculated_rate, self.minimum_rate)
            if increase_rate_left_of_minimum_flow_assuming_asv
            else rate + recirculated_rate
        )
        if rate_corrected_to_minimum_flow < self.minimum_rate or rate_corrected_to_minimum_flow > self.maximum_rate:
            point_is_valid = False
        else:
            point_is_valid = True

        return (
            point_is_valid,
            chart_area_flag,
            rate_corrected_to_minimum_flow,
        )

    def calculate_polytropic_head_and_efficiency_single_point(
        self,
        actual_rate_m3_per_hour: float,
        recirculated_rate_m3_per_hour: float = 0.0,
        increase_rate_left_of_minimum_flow_assuming_asv: bool = True,
    ) -> CompressorChartHeadEfficiencyResultSinglePoint:
        """Calculate polytropic head and efficiency for actual rate
        chart_area_flag may have three values, one for rates below minimum rate, one for rates between minimum and
        maximum rate and one for rates above maximum rate.

        :param actual_rate_m3_per_hour: Actual volumetric rate [Am3/h]
        :param increase_rate_left_of_minimum_flow_assuming_asv: True or False.
        """
        (
            point_is_valid,
            chart_area_flag,
            rate_corrected_to_minimum_flow,
        ) = self._evaluate_point_validity_chart_area_flag_and_adjusted_rate(
            rate=actual_rate_m3_per_hour,
            recirculated_rate=recirculated_rate_m3_per_hour,
            increase_rate_left_of_minimum_flow_assuming_asv=increase_rate_left_of_minimum_flow_assuming_asv,
        )

        polytropic_head = self.head_as_function_of_rate(rate_corrected_to_minimum_flow)
        polytropic_efficiency = self.efficiency_as_function_of_rate(rate_corrected_to_minimum_flow)

        return CompressorChartHeadEfficiencyResultSinglePoint(
            polytropic_head=polytropic_head,
            polytropic_efficiency=polytropic_efficiency,
            chart_area_flag=chart_area_flag,
            is_valid=point_is_valid,
        )
