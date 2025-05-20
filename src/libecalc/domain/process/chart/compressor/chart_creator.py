import numpy as np

from libecalc.common.serializable_chart import ChartCurveDTO, VariableSpeedChartDTO
from libecalc.domain.process.chart.compressor import VariableSpeedCompressorChart
from libecalc.domain.process.chart.compressor.generic_chart_data import (
    UNIFIED_GENERIC_CHART_CURVE_MAXIMUM_SPEED_HEADS,
    UNIFIED_GENERIC_CHART_CURVE_MAXIMUM_SPEED_RATES,
    UNIFIED_GENERIC_CHART_CURVE_MINIMUM_SPEED_HEADS,
    UNIFIED_GENERIC_CHART_CURVE_MINIMUM_SPEED_RATES,
)
from libecalc.domain.process.chart.compressor.types import CompressorChartResult
from libecalc.domain.process.chart.compressor.variable_speed_compressor_chart import (
    logger,
)
from libecalc.domain.process.compressor.core.train.utils.numeric_methods import (
    maximize_x_given_boolean_condition_function,
)


class CompressorChartCreator:
    @staticmethod
    def from_rate_and_head_values(
        actual_volume_rates_m3_per_hour: list[float],
        heads_joule_per_kg: list[float],
        polytropic_efficiency: float = 1,
    ) -> VariableSpeedCompressorChart:
        """Calculate a design point such that all input data are within capacity in the corresponding generic compressor
        chart and where the maximum speed curve are at the "maximum" input point.

        # Approach
        1. Scale the input data with an initial scaling such that for the corresponding unified generic chart maximum
           speed curve the maximum head is equal to maximum head in input data and maximum rate is equal to maximum rate
           in input data.
        2. Generate a variable speed compressor chart with design point (1, 1)
        3. Find the maximum rate of the compressor chart with design point (1, 1) using the scaled heads from the input
           data
        4. Check if any of the scaled points from the input data exceeds the capacity in the variable speed compressor
           chart with design point (1, 1)
           - If there are points below the stone wall, increase rate until no points are below stone wall. If there
             are any points above the maximum speed curve, iteratively increase the design rate and find the resulting
             design head giving no points below the stone wall. Stop when there are no points above maximum speed curve.
           - Else if there are points above the maximum speed curve, increase design head until one of the input points
             hits the stone wall. If there are no points above the maximum speed curve, reduce the head until no points
             are above the maximum speed curve. If there are still points above the maximum speed curve, iteratively
             increase the design rate and find the resulting design head giving no points below the stone wall.
             Stop when there are no points above maximum speed curve.
        5. If none of the scaled points input data exceeds the capacity in the variable speed compressor chart with
           design point (1, 1), there must be points that recirculate to the minimum rate/maximum head of the compressor
           chart, and one or more points exactly at the maximum rate/minimum head point of the maximum speed curve. In
           this (very unlikely) case the chart is perfect - return it.

        Args:
            actual_volume_rates_m3_per_hour: volume rate values [Am3/h]
            heads_joule_per_kg: Head values [J/kg]
            polytropic_efficiency: Polytropic efficiency as a fraction between 0 and 1.

        Returns:
            The resulting variable speed compressor chart
        """

        # Maximum values from unified generic chart
        maximum_rate_on_maximum_speed_curve_unified = UNIFIED_GENERIC_CHART_CURVE_MAXIMUM_SPEED_RATES[-1]
        maximum_head_on_maximum_speed_curve_unified = UNIFIED_GENERIC_CHART_CURVE_MAXIMUM_SPEED_HEADS[0]
        minimum_head_on_maximum_speed_curve_unified = UNIFIED_GENERIC_CHART_CURVE_MAXIMUM_SPEED_HEADS[-1]
        maximum_rate_on_minimum_speed_curve_unified = UNIFIED_GENERIC_CHART_CURVE_MINIMUM_SPEED_RATES[-1]
        maximum_change_in_rate_unified = (
            maximum_rate_on_maximum_speed_curve_unified - maximum_rate_on_minimum_speed_curve_unified
        )
        maximum_change_in_head_unified = (
            maximum_head_on_maximum_speed_curve_unified - minimum_head_on_maximum_speed_curve_unified
        )

        # Maximum values from input
        maximum_actual_rate = np.max(actual_volume_rates_m3_per_hour)
        maximum_head_value = np.max(heads_joule_per_kg)

        # Values to scale input with
        scaling_rate_to_unified = np.divide(maximum_actual_rate, maximum_rate_on_maximum_speed_curve_unified)
        scaling_head_to_unified = np.divide(maximum_head_value, maximum_head_on_maximum_speed_curve_unified)

        initial_design_head_unified = 1
        initial_design_rate_unified = 1

        def _create_compressor_chart_result_from_unified_design_point(
            unified_rate: float, unified_head: float
        ) -> CompressorChartResult:
            return CompressorChartCreator.from_rate_and_head_design_point(
                design_actual_rate_m3_per_hour=unified_rate * scaling_rate_to_unified,
                design_head_joule_per_kg=unified_head * scaling_head_to_unified,
                polytropic_efficiency=polytropic_efficiency,
            ).evaluate_capacity_and_extrapolate_below_minimum(
                actual_volume_rates=actual_volume_rates_m3_per_hour,
                heads=heads_joule_per_kg,
                extrapolate_heads_below_minimum=False,
            )

        initial_compressor_chart_result = _create_compressor_chart_result_from_unified_design_point(
            unified_rate=initial_design_rate_unified,
            unified_head=initial_design_head_unified,
        )

        design_rate_unified = initial_design_rate_unified
        design_head_unified = initial_design_head_unified

        maximum_design_rate_unified = initial_design_rate_unified + maximum_change_in_rate_unified
        maximum_design_head_unified = initial_design_head_unified + maximum_change_in_head_unified

        # Scenario 1: Point(s) below stone wall. First increase rate until there are no point(s) below stone wall.
        #             If there are still points above maximum speed curve, iteratively increase rate slightly and
        #             find corresponding head that gives no points below stone wall until no points are above
        #             maximum speed curve.
        if initial_compressor_chart_result.any_points_below_stone_wall:
            # Start with high design rate (all points above stone wall),
            # reduce it until the first point hits the stone wall
            design_rate_unified = maximum_design_rate_unified - maximize_x_given_boolean_condition_function(
                x_min=0,
                x_max=maximum_design_rate_unified - design_rate_unified,
                bool_func=lambda x: not _create_compressor_chart_result_from_unified_design_point(
                    unified_rate=maximum_design_rate_unified - x,
                    unified_head=design_head_unified,
                ).any_points_below_stone_wall,
            )
            while _create_compressor_chart_result_from_unified_design_point(
                unified_rate=design_rate_unified,
                unified_head=design_head_unified,
            ).any_points_above_maximum_speed_curve:
                # increase rate slightly, find head that gives no points below stone wall
                # repeat until no points above maximum speed curve
                design_rate_unified = design_rate_unified + 0.01  # increase rate with 1% of initial rate
                design_head_unified = maximize_x_given_boolean_condition_function(
                    x_min=design_head_unified,
                    x_max=maximum_design_head_unified,
                    bool_func=lambda x: not _create_compressor_chart_result_from_unified_design_point(
                        unified_rate=design_rate_unified,
                        unified_head=x,
                    ).any_points_below_stone_wall,
                )

        # Scenario 3: Point(s) above maximum speed curve. Increase head. Points can potentially end up on the stone
        #             wall. If any points do, both rate and head must be increased according to the slope of the
        #             stone wall (to stop points from falling under the stone wall)
        elif initial_compressor_chart_result.any_points_above_maximum_speed_curve:
            # First increase head until one point hits the stone wall
            design_head_unified = maximize_x_given_boolean_condition_function(
                x_min=design_head_unified,
                x_max=maximum_design_head_unified,
                bool_func=lambda x: not _create_compressor_chart_result_from_unified_design_point(
                    unified_rate=design_rate_unified,
                    unified_head=x,
                ).any_points_below_stone_wall,
            )
            # If no points are above the maximum speed curve, reduce head until one point hits the maximum speed curve
            if not _create_compressor_chart_result_from_unified_design_point(
                unified_rate=design_rate_unified,
                unified_head=design_head_unified,
            ).any_points_above_maximum_speed_curve:
                change_in_design_head_unified = maximize_x_given_boolean_condition_function(
                    x_min=0,
                    x_max=maximum_change_in_head_unified,
                    bool_func=lambda x: not _create_compressor_chart_result_from_unified_design_point(
                        unified_rate=design_rate_unified,
                        unified_head=design_head_unified - x,
                    ).any_points_above_maximum_speed_curve,
                )
                design_rate_unified = design_rate_unified - change_in_design_head_unified
            else:
                0.01 * design_rate_unified
                while _create_compressor_chart_result_from_unified_design_point(
                    unified_rate=design_rate_unified,
                    unified_head=design_head_unified,
                ).any_points_above_maximum_speed_curve:
                    # increase rate slightly, find head that gives no points below stone wall
                    # repeat until no points above maximum speed curve
                    design_rate_unified = design_rate_unified + 0.01  # increase rate with 1% of initial rate
                    design_head_unified = maximize_x_given_boolean_condition_function(
                        x_min=design_head_unified,
                        x_max=maximum_design_head_unified,
                        bool_func=lambda x: not _create_compressor_chart_result_from_unified_design_point(
                            unified_rate=design_rate_unified,
                            unified_head=x,
                        ).any_points_below_stone_wall,
                    )

        design_rate, design_head = (
            design_rate_unified * scaling_rate_to_unified,
            design_head_unified * scaling_head_to_unified,
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
            VariableSpeedChartDTO(
                curves=[
                    ChartCurveDTO(
                        rate_actual_m3_hour=list(min_speed_volume_rates),
                        polytropic_head_joule_per_kg=list(min_speed_heads),
                        efficiency_fraction=[polytropic_efficiency] * len(min_speed_volume_rates),
                        speed_rpm=75,  # 75 % of max speed
                    ),
                    ChartCurveDTO(
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
