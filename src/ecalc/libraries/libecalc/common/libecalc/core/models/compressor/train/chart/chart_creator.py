from typing import List

import numpy as np
from libecalc import dto
from libecalc.core.models.compressor.train.chart import VariableSpeedCompressorChart
from libecalc.core.models.compressor.train.chart.generic_chart_data import (
    UNIFIED_GENERIC_CHART_CURVE_MAXIMUM_SPEED_HEADS,
    UNIFIED_GENERIC_CHART_CURVE_MAXIMUM_SPEED_RATES,
    UNIFIED_GENERIC_CHART_CURVE_MINIMUM_SPEED_HEADS,
    UNIFIED_GENERIC_CHART_CURVE_MINIMUM_SPEED_RATES,
)
from libecalc.core.models.compressor.train.chart.variable_speed_compressor_chart import (
    logger,
)
from scipy.interpolate import interp1d
from shapely.geometry import LineString, Point


class CompressorChartCreator:
    @staticmethod
    def from_rate_and_head_values(
        actual_volume_rates_m3_per_hour: List[float],
        heads_joule_per_kg: List[float],
        polytropic_efficiency: float = 1,
    ) -> VariableSpeedCompressorChart:
        """Calculate a design point such that all input data are within capacity in the corresponding generic compressor
        chart and where the maximum speed curve are at the "maximum" input point.

        # Approach
        1. Scale the input data with an initial scaling such that for the corresponding unified generic chart maximum
           speed curve the maximum head is equal to maximum head in input data and maximum rate is equal to maximum rate
           in input data.
        2. Find the points not covered and find the point furthest above the initial chart.
            - Find the (unified) distance in rate and head directions from the point furthest above and the closest point
              on the initial chart
            - Adjust the design point such that the point furthest above will be covered by adding the distance found
        3. If no points are found above the initial chart, find the point closest to the maximum speed curve
           inside the chart
           - Find the (unified) distance in rate and head directions from the input point closest to the
              maximum speed curve and the closest point on the maximum speed curve on the initial chart
           - Adjust the design point such that the in put point closest to the maximum speed curve is just covered
              by subtracting the distance found

        :param actual_volume_rates_m3_per_hour: volume rate values [Am3/h]
        :param heads_joule_per_kg: Head values [J/kg]
        :param polytropic_efficiency: Polytropic efficiency as a fraction between 0 and 1.
        """
        maximum_speed_rates_unif = UNIFIED_GENERIC_CHART_CURVE_MAXIMUM_SPEED_RATES
        maximum_speed_heads_unif = UNIFIED_GENERIC_CHART_CURVE_MAXIMUM_SPEED_HEADS

        initial_design_rate_unif = maximum_speed_rates_unif[-1]
        initial_design_head_unif = maximum_speed_heads_unif[0]
        initial_head_interp_unif = interp1d(
            x=maximum_speed_rates_unif,
            y=maximum_speed_heads_unif,
            fill_value=np.inf,
            bounds_error=False,
        )
        maximum_actual_rate = np.max(actual_volume_rates_m3_per_hour)
        maximum_head_value = np.max(heads_joule_per_kg)
        initial_scaling_rate = np.divide(maximum_actual_rate, initial_design_rate_unif)
        initial_scaling_head = np.divide(maximum_head_value, initial_design_head_unif)

        initial_scaled_volume_rate = np.divide(actual_volume_rates_m3_per_hour, initial_scaling_rate)
        initial_scaled_head = np.divide(heads_joule_per_kg, initial_scaling_head)
        initial_max_head_for_rates_unif = initial_head_interp_unif(initial_scaled_volume_rate)
        indices_points_above_maximum = np.argwhere(initial_scaled_head > initial_max_head_for_rates_unif)[:, 0]

        line = LineString(zip(maximum_speed_rates_unif, maximum_speed_heads_unif))

        if any(indices_points_above_maximum):
            rates_for_distance_calculations = initial_scaled_volume_rate[indices_points_above_maximum]
            heads_for_distance_calculations = initial_scaled_head[indices_points_above_maximum]
        else:
            rates_for_distance_calculations = initial_scaled_volume_rate
            heads_for_distance_calculations = initial_scaled_head

        distances = [
            line.distance(Point(r, h)) for r, h in zip(rates_for_distance_calculations, heads_for_distance_calculations)
        ]
        distance_index = np.argmax(distances) if any(indices_points_above_maximum) else np.argmin(distances)

        max_point_rate = rates_for_distance_calculations[distance_index]
        max_point_head = heads_for_distance_calculations[distance_index]

        point_to_just_include = Point(max_point_rate, max_point_head)
        closest_point = line.interpolate(line.project(point_to_just_include))

        # (1 - (closest_point.x - point_to_just_include.x)) if no points above
        # but that equals (1 + point_to_just_include.x - closest_point.x)
        design_rate, design_head = (
            (1 + point_to_just_include.x - closest_point.x) * initial_scaling_rate,
            (1 + point_to_just_include.y - closest_point.y) * initial_scaling_head,
        )

        return CompressorChartCreator.from_rate_and_head_design_point(
            design_actual_rate_m3_per_hour=design_rate,
            design_head_joule_per_kg=design_head,
            polytropic_efficiency=polytropic_efficiency,
        )

    @staticmethod
    def from_rate_and_head_design_point(
        design_actual_rate_m3_per_hour: float,
        design_head_joule_per_kg: float,
        polytropic_efficiency: float,
    ) -> VariableSpeedCompressorChart:
        """A compressor chart based on a unified generic compressor chart scaled by a design rate and polytropic head point
        The chart has only two speed curves, 75% and 105% (of vendor reported maximum speed)
        :param design_actual_rate_m3_per_hour: Design rate [Am3/h]
        :param design_head_joule_per_kg: Design head [J/kg]
            note, head often denoted in mlc/m or kJ/kg. Input here is J/kg (not kJ/kg) as this is used for calculations
        :param polytropic_efficiency: Polytropic efficiency as a fraction between 0 and 1.
        """
        logger.debug(
            f"Creating VariableSpeedCompressorChartGeneric with"
            f"design_rate: {design_actual_rate_m3_per_hour},"
            f"design_head: {design_head_joule_per_kg},"
            f"polytropic_efficiency: {polytropic_efficiency}"
        )
        max_speed_volume_rates = design_actual_rate_m3_per_hour * UNIFIED_GENERIC_CHART_CURVE_MAXIMUM_SPEED_RATES
        min_speed_volume_rates = design_actual_rate_m3_per_hour * UNIFIED_GENERIC_CHART_CURVE_MINIMUM_SPEED_RATES
        max_speed_heads = design_head_joule_per_kg * UNIFIED_GENERIC_CHART_CURVE_MAXIMUM_SPEED_HEADS
        min_speed_heads = design_head_joule_per_kg * UNIFIED_GENERIC_CHART_CURVE_MINIMUM_SPEED_HEADS

        return VariableSpeedCompressorChart(
            dto.VariableSpeedChart(
                curves=[
                    dto.ChartCurve(
                        rate_actual_m3_hour=list(min_speed_volume_rates),
                        polytropic_head_joule_per_kg=list(min_speed_heads),
                        efficiency_fraction=[polytropic_efficiency] * len(min_speed_volume_rates),
                        speed_rpm=75,  # 75 % of max speed
                    ),
                    dto.ChartCurve(
                        rate_actual_m3_hour=list(max_speed_volume_rates),
                        polytropic_head_joule_per_kg=list(max_speed_heads),
                        efficiency_fraction=[polytropic_efficiency] * len(max_speed_volume_rates),
                        speed_rpm=105,  # 105 % of max speed.
                    ),
                ],
                design_head=design_head_joule_per_kg,
                design_rate=design_actual_rate_m3_per_hour,
            )
        )
