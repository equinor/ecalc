from __future__ import annotations

from copy import deepcopy

import numpy as np
from numpy.typing import NDArray
from scipy.interpolate import interp1d

from libecalc.common.errors.exceptions import IllegalStateException
from libecalc.common.logger import logger
from libecalc.domain.process.chart import VariableSpeedChart
from libecalc.domain.process.chart.chart_area_flag import ChartAreaFlag
from libecalc.domain.process.chart.compressor.types import (
    CompressorChartHeadEfficiencyResultSinglePoint,
    CompressorChartResult,
)

NUMERICAL_TOLERANCE = 1e-7


class VariableSpeedCompressorChart(VariableSpeedChart):
    def get_chart_adjusted_for_control_margin(self, control_margin: float | None) -> VariableSpeedCompressorChart:
        """Sets a new minimum rate and corresponding head and efficiency for each curve in a compressor chart."""
        if control_margin is None:
            return deepcopy(self)

        new_chart = deepcopy(self)
        new_chart.curves = [
            curve.adjust_for_control_margin(control_margin=control_margin) for curve in new_chart.curves
        ]

        return new_chart

    def get_maximum_rate(
        self,
        heads: NDArray[np.float64],
        extrapolate_heads_below_minimum: bool,
    ):
        """The maximum rate for a given head value, will in general be defined by the maximum speed curve
        However, if downstream choking is not allowed, i.e. the head values below defined are not allowed to be lifted,
        the maximum rate will be defined by stone wall for head values below the maximum speed defined head range
        Stone wall is defined by the "right wall" in the compressor chart, the maximum rate values for each speed
        In this generic chart, there are only two speed curves and stone wall is thus defined as the line between
        the maximum speed curves maximum rate point and the minimum speed curves maximum rate point.

        As this function is only called for a very few cases, the maximum rate interpolation functions are set up when
        needed and not at initialization of the compressor chart object.


        :param heads: Head values [J/kg]
        :param extrapolate_heads_below_minimum: True or False if we want to extrapolate below minimum speed.
            If part of a train, one can not assume the speed is increased up to stone-wall and further choked
            downstream to meet requested pressure. For a single compressor, this may be the case. Even though it's a
            rare condition, theoretically it is possible, and we need to have a well-defined model also outside the most
            common operating range.
        """
        if extrapolate_heads_below_minimum:
            maximum_rate_function = self.maximum_rate_as_function_of_head
        else:
            maximum_rate_function = self.maximum_rate_as_function_of_head_no_choking

        return maximum_rate_function(heads)

    def evaluate_capacity_and_extrapolate_below_minimum(
        self,
        actual_volume_rates: NDArray[np.float64] | float,
        heads: NDArray[np.float64] | float,
        extrapolate_heads_below_minimum: bool,
    ) -> CompressorChartResult:
        """Evaluate if (rate, head)-point is inside chart
        if inside, return point as is
        if rate is to the "left" of min flow, return rate equal to min flow (+ info about move, i.e. recirculation status)
        if head "below" minimum speed head return head equal to minimum speed? This will be an invalid point if all
        compressors are on the same shaft (or the speed have to be increased for the entire train/common shaft).

        for rates above maximum rate and heads above maximum heads, invalid status should be returned and not
        energy computation carried out for this point as it is infeasible

        :param actual_volume_rates: Actual volumetric volume rates [Am3/h]
        :param heads: Head values [J/kg]
        :param extrapolate_heads_below_minimum: True or False if we want to extrapolate below minimum speed.
        """
        actual_volume_rates = np.atleast_1d(actual_volume_rates)
        heads = np.atleast_1d(heads)
        minimum_flow_function = (
            self.minimum_rate_as_function_of_head
            if extrapolate_heads_below_minimum
            else self.minimum_rate_as_function_of_head_no_choking
        )
        minimum_rates = minimum_flow_function(heads)
        rate_has_recirc = actual_volume_rates < minimum_rates
        asv_corrected_rates = np.fmax(minimum_rates, actual_volume_rates)

        minimum_head_values = self.minimum_head_as_function_of_rate(asv_corrected_rates)
        if extrapolate_heads_below_minimum:
            pressure_is_choked = heads < minimum_head_values
            choke_corrected_heads = np.fmax(minimum_head_values, heads)
            pressure_is_below_minimum = np.full_like(rate_has_recirc, False)
        else:
            choke_corrected_heads = heads
            pressure_is_choked = np.full_like(heads, False, dtype=bool)
            pressure_is_below_minimum = heads < minimum_head_values

        # Set rates above maximum to nan as these are infeasible
        maximum_rate_function = (
            self.maximum_rate_as_function_of_head
            if extrapolate_heads_below_minimum
            else self.maximum_rate_as_function_of_head_no_choking
        )
        maximum_rates = maximum_rate_function(heads)
        rate_exceeds_maximum = asv_corrected_rates > maximum_rates

        # Set heads above maximum to nan as these are infeasible
        maximum_heads = self.maximum_head_as_function_of_rate(actual_volume_rates)
        head_exceeds_maximum = choke_corrected_heads > maximum_heads

        exceeds_capacity = np.asarray(~(~rate_exceeds_maximum & ~head_exceeds_maximum & ~pressure_is_below_minimum))

        return CompressorChartResult(
            asv_corrected_rates=list(asv_corrected_rates),
            choke_corrected_heads=list(choke_corrected_heads),
            rate_has_recirc=list(rate_has_recirc),
            pressure_is_choked=list(pressure_is_choked),
            rate_exceeds_maximum=list(rate_exceeds_maximum),
            head_exceeds_maximum=list(head_exceeds_maximum),
            exceeds_capacity=list(exceeds_capacity),
        )

    """
    Below we setup functions to be able to calculate polytropic head and efficiency for rates below minimum and above maximum,
    i.e. for rates outside the chart.

    Note: We do this because these are used in an Newton-iteration based on gradients in an outer loop,
    we want to return the extrapolated values outside the defined area and return together with an attribute
    telling if this is valid or not. Then, when using starting points in the iteration which is perhaps outside
    the chart, one will still be able to calculate the gradients to go further in the iteration.
    """

    @property
    def head_as_function_of_speed_for_rates_below_minimum_extrapolation(self) -> interp1d:
        return interp1d(
            x=self.speed_values,
            y=[x.rate_head_and_efficiency_at_minimum_rate[1] for x in self.curves],
            bounds_error=False,
            fill_value=(
                [x.rate_head_and_efficiency_at_minimum_rate[1] for x in self.curves][0],
                [x.rate_head_and_efficiency_at_minimum_rate[1] for x in self.curves][-1],
            ),
        )

    @property
    def efficiency_as_function_of_speed_for_rates_below_minimum_extrapolation(self) -> interp1d:
        return interp1d(
            x=self.speed_values,
            y=[x.rate_head_and_efficiency_at_minimum_rate[2] for x in self.curves],
            bounds_error=False,
            fill_value=(
                [x.rate_head_and_efficiency_at_minimum_rate[2] for x in self.curves][0],
                [x.rate_head_and_efficiency_at_minimum_rate[2] for x in self.curves][-1],
            ),
        )

    @property
    def head_as_function_of_speed_for_rates_above_maximum_extrapolation(self):
        return interp1d(
            x=self.speed_values,
            y=[x.rate_head_and_efficiency_at_maximum_rate[1] for x in self.curves],
            bounds_error=False,
            fill_value=(
                [x.rate_head_and_efficiency_at_maximum_rate[1] for x in self.curves][0],
                [x.rate_head_and_efficiency_at_maximum_rate[1] for x in self.curves][-1],
            ),
        )

    @property
    def efficiency_as_function_of_speed_for_rates_above_maximum_extrapolation(self) -> interp1d:
        return interp1d(
            x=self.speed_values,
            y=[x.rate_head_and_efficiency_at_maximum_rate[2] for x in self.curves],
            bounds_error=False,
            fill_value=(
                [x.rate_head_and_efficiency_at_maximum_rate[2] for x in self.curves][0],
                [x.rate_head_and_efficiency_at_maximum_rate[2] for x in self.curves][-1],
            ),
        )

    def calculate_polytropic_head_and_efficiency_single_point(
        self,
        speed: float,
        actual_rate_m3_per_hour: float,
        recirculated_rate_m3_per_hour: float = 0.0,
        increase_speed_below_assuming_choke: bool = False,
        increase_rate_left_of_minimum_flow_assuming_asv: bool = True,
    ) -> CompressorChartHeadEfficiencyResultSinglePoint:
        """Calculate polytropic head and corresponding efficiency given speed and actual volume rate
        Returns polytropic head (in Joule_per_kg), polytropic_efficiency and a flag to indicate placement of the
        requested point relative to the chart.

        :param speed: [rpm]
        :param actual_rate_m3_per_hour: [Am3/h]
        :param increase_speed_below_assuming_choke: True or False
        :param increase_rate_left_of_minimum_flow_assuming_asv: True or False
        """
        (
            point_is_valid,
            chart_area_flag,
            speed_adjusted,
            rate_adjusted,
        ) = self._evaluate_point_validity_chart_area_flag_and_adjusted_speed_and_rate(
            speed=speed,
            increase_speed_below_assuming_choke=increase_speed_below_assuming_choke,
            rate=actual_rate_m3_per_hour,
            recirculated_rate=recirculated_rate_m3_per_hour,
            increase_rate_left_of_minimum_flow_assuming_asv=increase_rate_left_of_minimum_flow_assuming_asv,
        )

        (
            polytropic_head,
            polytropic_efficiency,
        ) = self._calculate_polytropic_head_and_efficiency(
            point_is_valid=point_is_valid, speed=speed_adjusted, rate=rate_adjusted, chart_area_flag=chart_area_flag
        )

        return CompressorChartHeadEfficiencyResultSinglePoint(
            polytropic_head=float(polytropic_head),
            polytropic_efficiency=float(polytropic_efficiency),
            chart_area_flag=chart_area_flag,
            is_valid=point_is_valid,
        )

    def _evaluate_point_validity_chart_area_flag_and_adjusted_speed_and_rate(
        self,
        speed: float,
        increase_speed_below_assuming_choke: bool,
        rate: float,
        recirculated_rate: float,
        increase_rate_left_of_minimum_flow_assuming_asv: bool,
    ) -> tuple[bool, ChartAreaFlag, float, float]:
        """Evaluate position of point relative to chart
        Set a chart area flag based on position. Differ between internal points, speed values below and above minimum
        and maximum, rate values below and above minimum and maximum, and the cases when speed has been increased and
        rate outside minimum/maximum range
        Determine whether point is valid
        Adjust values for speed and rate for calculation according to
         1. Possible rate adjustment due to assumed anti-surge control (minimum flow)
         2. Possible speed adjustment due to assumed down or up stream choking.

        Note: We do this because the chart area flag is used for both giving the user output about where the initial
            calculation point is relative to the chart area (i.e. if it is originally left of minimum flow, but moved to
            minimum flow to mimic asv, the user wants to know this for the analysis. Also the point validity is used
            further out in iterations to meet pressure targets, and one need to get information about if the point
            is valid (within capacity) or not.

        Args:
            speed: the speed related to the operation point [rpm]
            increase_speed_below_assuming_choke: boolean telling whether the speed related to an operation point should
              be changed to the minimum speed if the speed is below the minimum speed (assumes up/down-stream choking)
            rate: the actual inlet flow rate of the operation point [Am3/h]
            recirculated_rate: potential additional flow rate introduced by the anti-surge valve for pressure control
            increase_rate_left_of_minimum_flow_assuming_asv: boolean telling whether the actual flow rate should be
              automatically changed to the minimum flow rate for the compressor chart when below the minimum flow rate

        Returns:
            A tuple of values describing if the operation point is valid, information about where the operation
            point is placed relative to the compressor chart, and the (potentially updated) values for speed and rate
        """
        point_is_valid = True
        chart_area_flag = ChartAreaFlag.INTERNAL_POINT
        speed_to_use = speed
        rate_to_use = rate + recirculated_rate
        speed_is_increased = False
        if speed < self.minimum_speed:
            chart_area_flag = ChartAreaFlag.BELOW_MINIMUM_SPEED
            if increase_speed_below_assuming_choke:
                speed_to_use = self.minimum_speed
                speed_is_increased = True
            else:
                point_is_valid = False
        elif speed > self.maximum_speed:
            chart_area_flag = ChartAreaFlag.ABOVE_MAXIMUM_SPEED
            point_is_valid = False

        if point_is_valid:
            # Todo: Need to QA this logic. Below minimum speed requires speed < minimum_speed, but this is not enforced?
            minimum_flow_rate_for_speed = self.minimum_rate_as_function_of_speed(speed_to_use)
            maximum_flow_rate_for_speed = self.maximum_rate_as_function_of_speed(speed_to_use)
            # first update rate_to_use when below minimum flow if increase_rate_left_of_minimum_flow_assuming_asv
            if rate_to_use < minimum_flow_rate_for_speed:
                if increase_rate_left_of_minimum_flow_assuming_asv:
                    rate_to_use = minimum_flow_rate_for_speed
                else:
                    point_is_valid = False
            # second, decide ChartAreaFlag based on the original rate input
            if rate == 0:
                chart_area_flag = ChartAreaFlag.NO_FLOW_RATE
            elif rate < minimum_flow_rate_for_speed:
                chart_area_flag = (
                    ChartAreaFlag.BELOW_MINIMUM_SPEED_AND_BELOW_MINIMUM_FLOW_RATE
                    if speed_is_increased
                    else ChartAreaFlag.BELOW_MINIMUM_FLOW_RATE
                )
            elif rate > maximum_flow_rate_for_speed:
                chart_area_flag = (
                    ChartAreaFlag.BELOW_MINIMUM_SPEED_AND_ABOVE_MAXIMUM_FLOW_RATE
                    if speed_is_increased
                    else ChartAreaFlag.ABOVE_MAXIMUM_FLOW_RATE
                )
                point_is_valid = False

        return point_is_valid, chart_area_flag, speed_to_use, rate_to_use

    def _calculate_polytropic_head_and_efficiency(
        self,
        point_is_valid: bool,
        speed: float,
        rate: float,
        chart_area_flag: ChartAreaFlag,
    ) -> tuple[float, float]:
        """Calculate polytropic head and efficiency
        If the point is not valid, nan will be returned for both
        If the point is valid and the speed is equal to one of the input curves, this curve will be used
        If the point is valid and the speed is not defined in the input data, interpolation will be done based on the two
        closest curves below and above the requested speed.

        speed: [rpm]
        rate: [Am3/h]
        """
        if point_is_valid:
            chart_curve_at_given_speed = self.get_curve_by_speed(speed=speed)
            if chart_curve_at_given_speed is not None:
                # The speed requested is contained in the input data, and interpolation on speed not necessary
                # All computations done on the corresponding speed curve
                polytropic_head = float(chart_curve_at_given_speed.head_as_function_of_rate(rate))
                polytropic_efficiency = float(chart_curve_at_given_speed.efficiency_as_function_of_rate(rate))
            else:
                (
                    polytropic_head,
                    polytropic_efficiency,
                ) = self.calculate_head_and_efficiency_for_internal_point_between_given_speeds(
                    speed=speed,
                    rate=rate,
                )
        else:
            (
                polytropic_head,
                polytropic_efficiency,
            ) = self._calculate_extrapolated_values_for_external_points(
                speed=speed,
                chart_area_flag=chart_area_flag,
            )

        return polytropic_head, polytropic_efficiency

    def calculate_head_and_efficiency_for_internal_point_between_given_speeds(
        self, speed: float, rate: float
    ) -> tuple[float, float]:
        """When the requested speed is not contained in the input data, interpolation is done both wrt speed and rate.
        1. A weight factor is calculated for the above and below result based on the distance to each of these from the
           requested speed
        2. This weight factor is then used to compute an equivalent minimum and maximum rate for the requested speed
            which is then used to compute a scaled (on 0 to 1) rate from minimum to maximum
        3. Equivalent rates for the speed above and below is computed between each of their minimum and maximum and the
           scaled rate
        4. The equivalent rates are used to calculate polytropic head and efficiency on the corresponding chart curves
            for the speed below and above
        5. The final polytropic head and efficiency for the requested speed is found by weighting the equivalent values
            for the speeds below and above.

        Note:
            We need to calculate head and efficiency values for calculations. The chart is a discrete representation of
            a continuum, thus we interpolate between the defined points.

        :param speed: [rpm]
        :param rate: [Am3/h]
        """
        # Find speed curves to use for computations. Find the one closes to requested speed above and below
        # and interpolate based on these
        speed_curve_below = self.closest_curve_below_speed(speed=speed)
        speed_curve_above = self.closest_curve_above_speed(speed=speed)

        # If any of speed_below or speed_above is nan, it means that the point is not internal after all
        if speed_curve_below is None or speed_curve_above is None:
            min_allowed_speed, *_, max_allowed_speed = sorted(self.speed_values)
            msg = (
                f"The requested speed ({str(speed)}) is outside the allowed speed range "
                f"({str(min_allowed_speed)}-{str(max_allowed_speed)}). You should not get here, please contact "
                f"support."
            )
            logger.exception(msg)
            raise IllegalStateException(msg)

        (
            scaling_factor_below,
            scaling_factor_above,
        ) = self._calculate_scaling_factors_for_speed_below_and_above(
            speed=speed,
            speed_below=speed_curve_below.speed,
            speed_above=speed_curve_above.speed,
        )

        (
            equivalent_rate_speed_below,
            equivalent_rate_speed_above,
        ) = self._calculate_equivalent_rates_for_speed_below_and_above(
            minimum_rate_speed_above=speed_curve_above.minimum_rate,
            maximum_rate_speed_above=speed_curve_above.maximum_rate,
            minimum_rate_speed_below=speed_curve_below.minimum_rate,
            maximum_rate_speed_below=speed_curve_below.maximum_rate,
            scaling_factor_below=scaling_factor_below,
            scaling_factor_above=scaling_factor_above,
            rate=rate,
        )

        polytropic_head_speed_below = float(speed_curve_below.head_as_function_of_rate(equivalent_rate_speed_below))
        polytropic_efficiency_speed_below = float(
            speed_curve_below.efficiency_as_function_of_rate(equivalent_rate_speed_below)
        )
        polytropic_head_speed_above = float(speed_curve_above.head_as_function_of_rate(equivalent_rate_speed_above))
        polytropic_efficiency_speed_above = float(
            speed_curve_above.efficiency_as_function_of_rate(equivalent_rate_speed_above)
        )

        polytropic_head_for_speed = (
            polytropic_head_speed_below * scaling_factor_below + polytropic_head_speed_above * scaling_factor_above
        )
        polytropic_efficiency_for_speed = (
            polytropic_efficiency_speed_below * scaling_factor_below
            + polytropic_efficiency_speed_above * scaling_factor_above
        )
        return polytropic_head_for_speed, polytropic_efficiency_for_speed

    def _calculate_extrapolated_values_for_external_points(
        self, speed: float, chart_area_flag: ChartAreaFlag
    ) -> tuple[float, float]:
        """Return extrapolated values for points within speed range
        These are not valid for use, but needed for e.g. iterations in a compressor train
        Upon usage, one must ensure that the point is valid.
        """
        if chart_area_flag in (
            ChartAreaFlag.BELOW_MINIMUM_SPEED,
            ChartAreaFlag.ABOVE_MAXIMUM_SPEED,
        ):
            polytropic_head, polytropic_efficiency = np.nan, np.nan
        elif chart_area_flag in (
            ChartAreaFlag.ABOVE_MAXIMUM_FLOW_RATE,
            ChartAreaFlag.BELOW_MINIMUM_SPEED_AND_ABOVE_MAXIMUM_FLOW_RATE,
        ):
            polytropic_head = self.head_as_function_of_speed_for_rates_above_maximum_extrapolation(speed)
            polytropic_efficiency = self.efficiency_as_function_of_speed_for_rates_above_maximum_extrapolation(speed)
        elif chart_area_flag in (
            ChartAreaFlag.BELOW_MINIMUM_FLOW_RATE,
            ChartAreaFlag.BELOW_MINIMUM_SPEED_AND_BELOW_MINIMUM_FLOW_RATE,
        ):
            polytropic_head = self.head_as_function_of_speed_for_rates_below_minimum_extrapolation(speed)
            polytropic_efficiency = self.efficiency_as_function_of_speed_for_rates_below_minimum_extrapolation(speed)
        else:
            msg = (
                f"You should not enter here, please contact support. (Dead end for variable speed compressor "
                f"chart evaluation, chart area flag: {str(chart_area_flag)})"
            )
            logger.exception(msg)
            raise IllegalStateException(msg)

        return polytropic_head, polytropic_efficiency

    @staticmethod
    def _calculate_scaling_factors_for_speed_below_and_above(
        speed: float, speed_above: float, speed_below: float
    ) -> tuple[float, float]:
        """Calculate weight factor between speed curve above and below.

        :param speed: [rpm]
        :param speed_above: [rpm]
        :param speed_below: [rpm]
        """
        distance_above = speed_above - speed
        distance_below = speed - speed_below
        total_distance_above_below = distance_above + distance_below
        scaling_factor_below = 0.0 if total_distance_above_below == 0.0 else distance_above / total_distance_above_below
        scaling_factor_above = 1.0 - scaling_factor_below
        return scaling_factor_below, scaling_factor_above

    @staticmethod
    def _calculate_equivalent_rates_for_speed_below_and_above(
        minimum_rate_speed_below: float,
        maximum_rate_speed_below: float,
        minimum_rate_speed_above: float,
        maximum_rate_speed_above: float,
        scaling_factor_below: float,
        scaling_factor_above: float,
        rate: float,
    ) -> tuple[float, float]:
        """Speed [rpm]
        rate [Am3/h].

        Calculate equivalent rates for the speed below and above the requested speed.
        """
        scaled_minimum_rate = (
            scaling_factor_below * minimum_rate_speed_below + scaling_factor_above * minimum_rate_speed_above
        )
        scaled_maximum_rate = (
            scaling_factor_below * maximum_rate_speed_below + scaling_factor_above * maximum_rate_speed_above
        )
        # If rate is not in the interval between minimum and maximum scaled rates, the point is not internal and the method
        # is not valid
        # Allow a numerical tolerance here as the minimum and maximum rates are calculated with interpolation and
        # the code will not fail if the rate value falls outside
        if (rate > scaled_maximum_rate and abs(rate - scaled_maximum_rate) > NUMERICAL_TOLERANCE) or (
            rate < scaled_minimum_rate and abs(rate - scaled_minimum_rate) > NUMERICAL_TOLERANCE
        ):
            msg = (
                f"The requested rate ({str(rate)}) is outside the allowed rate range "
                f"({str(scaled_minimum_rate)}-{str(scaled_maximum_rate)}). You should not get here, please "
                f"contact support."
            )
            logger.exception(msg)
            raise IllegalStateException(msg)

        # A scaled rate within 0 and 1, indicating the "portion/fraction" of the entire rate interval
        scaled_rate_within_capacity = (rate - scaled_minimum_rate) / (scaled_maximum_rate - scaled_minimum_rate)

        equivalent_rate_speed_above = (
            minimum_rate_speed_above
            + (maximum_rate_speed_above - minimum_rate_speed_above) * scaled_rate_within_capacity
        )
        equivalent_rate_speed_below = (
            minimum_rate_speed_below
            + (maximum_rate_speed_below - minimum_rate_speed_below) * scaled_rate_within_capacity
        )
        return equivalent_rate_speed_below, equivalent_rate_speed_above
