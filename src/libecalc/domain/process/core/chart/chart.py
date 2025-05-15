from copy import deepcopy
from typing import Literal, Self

import numpy as np
from numpy.typing import NDArray
from scipy.interpolate import interp1d
from shapely.geometry import LineString, Point

from libecalc.common.chart_type import ChartType
from libecalc.common.list.list_utils import array_to_list
from libecalc.domain.component_validation_error import ProcessChartValueValidationException
from libecalc.domain.process.core.chart.chart_area_flag import ChartAreaFlag


class ChartCurve:
    """Compressor or pump chart curve at a given speed. Multiple chart curves results in a complete map for a variable
    speed chart. A single speed chart has only a single curve.

    Units for both pump and compressor charts:
        Rate [Am3/h]
        Head [J/kg]
        Efficiency as fraction (0, 1]
        Optional axial speed [rpm]

    Note that pump charts are normally converted from meter liquid column to J/kg before or when creating the chart.
    """

    def __init__(
        self,
        rate_actual_m3_hour: list[float],
        polytropic_head_joule_per_kg: list[float],
        efficiency_fraction: list[float],
        speed_rpm: float,
    ):
        # Validate rate_actual_m3_hour
        if not all(x >= 0 for x in rate_actual_m3_hour):
            raise ProcessChartValueValidationException(message="All values in rate_actual_m3_hour must be >= 0")

        # Validate polytropic_head_joule_per_kg
        if not all(x >= 0 for x in polytropic_head_joule_per_kg):
            raise ProcessChartValueValidationException(
                message="All values in polytropic_head_joule_per_kg must be >= 0"
            )

        # Validate efficiency_fraction
        if not all(0 < x <= 1 for x in efficiency_fraction):
            raise ProcessChartValueValidationException(
                message="All values in efficiency_fraction must be in the range (0, 1]"
            )

        # Validate speed_rpm
        if speed_rpm < 0:
            raise ProcessChartValueValidationException(message="speed_rpm must be >= 0")

        self.rate_actual_m3_hour = rate_actual_m3_hour
        self.polytropic_head_joule_per_kg = polytropic_head_joule_per_kg
        self.efficiency_fraction = efficiency_fraction
        self.speed_rpm = speed_rpm

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

    @property
    def rate_values(self) -> NDArray[np.float64]:
        return np.asarray(self.rate)

    @property
    def head_values(self) -> NDArray[np.float64]:
        return np.asarray(self.head)

    @property
    def efficiency_values(self) -> NDArray[np.float64] | None:
        return np.asarray(self.efficiency)

    @property
    def is_100_percent_efficient(self) -> bool:
        """Check if all efficiencies are 100%."""
        return np.all(self.efficiency_values == 1)

    @property
    def minimum_rate(self) -> float:
        return self.rate[0]

    @property
    def maximum_rate(self) -> float:
        return self.rate[-1]

    @property
    def efficiency_as_function_of_rate(self) -> interp1d:
        """Efficiency = f(rate)."""
        return interp1d(
            x=self.rate_values,
            y=self.efficiency_values,
            fill_value=(self.efficiency_values[0], self.efficiency_values[-1])
            if self.efficiency_values is not None
            else ("NaN", "NaN"),
            bounds_error=False,
        )

    @property
    def head_as_function_of_rate(self) -> interp1d:
        """Head = f(rate)."""
        return interp1d(
            x=self.rate_values,
            y=self.head_values,
            fill_value=(self.head_values[0], self.head_values[-1]),
            bounds_error=False,
        )

    @property
    def rate_as_function_of_head(self) -> interp1d:
        """Rate = f(head)."""
        # Inverse monotonic function, that´s why we know that the correct values are (last, first)
        return interp1d(
            x=self.head_values,
            y=self.rate_values,
            fill_value=(self.rate_values[-1], self.rate_values[0]),
            bounds_error=False,
        )

    @property
    def rate_as_function_of_head_extrapolate(self) -> interp1d:
        """Rate = f(head)."""
        # Inverse monotonic function, that´s why we know that the correct values are (last, first)
        return interp1d(
            x=self.head_values,
            y=self.rate_values,
            fill_value="extrapolate",
            bounds_error=False,
        )

    @property
    def rate_head_and_efficiency_at_minimum_rate(self) -> tuple[float, float, float]:
        """Return data point (rate, head, efficiency) for the minimum rate value."""
        return self.rate[0], self.head[0], self.efficiency[0]

    @property
    def rate_head_and_efficiency_at_maximum_rate(self) -> tuple[float, float, float]:
        """Return data point (rate, head, efficiency) for the maximum rate value (Top of stone wall)."""
        return self.rate[-1], self.head[-1], self.efficiency[-1]

    def get_distance_and_efficiency_from_closest_point_on_curve(self, rate: float, head: float) -> tuple[float, float]:
        """Compute the closest distance from a point (rate,head) to the (interpolated) curve and corresponding
        efficiency for that closest point.
        """
        head_linestring = LineString(list(zip(self.rate_values, self.head_values)))
        p = Point(rate, head)

        distance = p.distance(head_linestring)
        closest_interpolated_point = head_linestring.interpolate(head_linestring.project(p))
        if closest_interpolated_point.y < p.y:
            distance = -distance
        efficiency = float(self.efficiency_as_function_of_rate(closest_interpolated_point.x))
        return distance, efficiency

    def adjust_for_control_margin(self, control_margin: float | None) -> Self:
        """Adjusts the chart curve with respect to the given control margin.

        Args:
            control_margin: a fraction on the interval [0, 1]

        Returns:
            Chart curve where lowest fraction (given by control margin) of rates have been removed and the
            head/efficiency updated accordingly for the new minimum rate point on the curve
        """
        if control_margin is None:
            return deepcopy(self)

        def _get_new_point(x: list[float], y: list[float], new_x_value) -> float:
            """Set up simple interpolation and get a point estimate on y based on the new x point."""
            return interp1d(x=x, y=y, fill_value=(np.min(y), np.max(y)), bounds_error=False, assume_sorted=False)(
                new_x_value
            )

        adjust_minimum_rate_by = (np.max(self.rate) - np.min(self.rate)) * control_margin
        new_minimum_rate = np.min(self.rate) + adjust_minimum_rate_by
        rate_head_efficiency_array = np.vstack((self.rate, self.head, self.efficiency))
        # remove points with rate less than the new minimum rate (i.e. chop off left part of chart curve)
        rate_head_efficiency_array = rate_head_efficiency_array[:, rate_head_efficiency_array[0, :] > new_minimum_rate]

        new_rate_head_efficiency_point = [
            new_minimum_rate,
            _get_new_point(x=self.rate, y=self.head, new_x_value=new_minimum_rate),  # Head as a function of rate
            _get_new_point(  # Efficiency as a function of rate
                x=self.rate, y=self.efficiency, new_x_value=new_minimum_rate
            ),
        ]

        rate_head_efficiency_array = np.c_[
            new_rate_head_efficiency_point,
            rate_head_efficiency_array,
        ]

        new_chart_curve = deepcopy(self)

        new_chart_curve.rate_actual_m3_hour = rate_head_efficiency_array[0, :].tolist()
        new_chart_curve.polytropic_head_joule_per_kg = rate_head_efficiency_array[1, :].tolist()
        new_chart_curve.efficiency_fraction = rate_head_efficiency_array[2, :].tolist()

        return new_chart_curve


class SingleSpeedChart(ChartCurve):
    """A single speed chart is just one ChartCurve.

    Here we may implement methods that is not relevant for single chart curves but for a single speed equipment.

    The reason for this subclass is that we already use the naming convention single and variable speed equipment.

    Note: For a single speed chart the speed is optional, but it is good practice to include it.
    """

    typ: Literal[ChartType.SINGLE_SPEED] = ChartType.SINGLE_SPEED

    def get_chart_area_flag(self, rate: float) -> ChartAreaFlag:
        """Set chart area flag based on rate [Am3/h]."""
        if rate < self.minimum_rate:
            chart_area_flag = ChartAreaFlag.BELOW_MINIMUM_FLOW_RATE
        elif rate > self.maximum_rate:
            chart_area_flag = ChartAreaFlag.ABOVE_MAXIMUM_FLOW_RATE
        else:
            # For single speed charts, the point is interpreted as internal if rate is between minimum and maximum rate
            chart_area_flag = ChartAreaFlag.INTERNAL_POINT
        return chart_area_flag

    @property
    def minimum_speed(self) -> float:
        """Used to handle single speed and variable speed charts generically."""
        return self.speed_rpm if self.speed_rpm else np.nan

    @property
    def maximum_speed(self) -> float:
        """Used to handle single speed and variable speed charts generically."""
        return self.speed_rpm if self.speed_rpm else np.nan


class VariableSpeedChart:
    """When talking about variable speed charts, it is important to understand the different components of a the chart:

    y-axis = head [kJ/kg]
    x-axis = actual volume rate [Am3/hr]  # For pumps the Am3/h3 ~ m3/hr since water is essentially incompressible.

    Areas of the chart:
        1. Minimum speed curve
        2. Maximum speed curve
        3. Stone wall (maximum flow) -> the right hand side of the chart. i.e. the max rates for each speed curve
        4. Minimum flow

    Note that speed increases (z-axis) with increased head and rate, and is projected into a the xy-plane in this
    sketch. The efficiency dimension is not visualized here.


                                                            (.
                                                     (             (
                                                   .                    /

                                                ,                               .
                                              (                                     /
                                                                                        .  (2) Maximum speed curve
                                                                                           (
                                         (                                                    (
                                       /                                                         .
    y-axis: Head [kJ/kg]             /                                                              #
                                                                                                      (
                                  (                                                                     #
                                .                                                                         /
                                                                                                            .
                             ,  (4) Minimum flow line
                           (                                                                                   /

                                                                                                                  .
                      (                                                                                           (
                    *                                                                                        (
                                                                                                        #
                                                                                                   (
               (                                                                              (
                                                                                         (
                                                                                    *
          *                                                                    ,
        (                                                                 .       (3)  Maximum flow line (stonewall)
                                                                      .
      (                                                          *
            ./                                              *
                    (                                  (
                         ,                        (
    (1) Minimum speed curve  /               (
                                ,       #

                            x-axis: Volume rate -> [Am3/hr or m3/hr]

    """

    typ: Literal[ChartType.VARIABLE_SPEED] = ChartType.VARIABLE_SPEED

    def __init__(
        self,
        curves: list[ChartCurve],
        control_margin: float | None = None,  # Todo: Raise warning if this is used in an un-supported model.
        design_rate: float | None = None,
        design_head: float | None = None,
    ):
        # Validate and transform curves
        self.curves = [ChartCurve(**curve) if isinstance(curve, dict) else curve for curve in curves]

        if not all(isinstance(curve, ChartCurve) for curve in self.curves):
            raise TypeError("All items in curves must be instances of ChartCurve or valid dictionaries.")

        # Validate design_rate
        if design_rate is not None and design_rate < 0:
            raise ProcessChartValueValidationException(message="Design rate must be >= 0.")

        # Validate design_head
        if design_head is not None and design_head < 0:
            raise ProcessChartValueValidationException(message="Design head must be >= 0.")

        self.curves = curves
        self.control_margin = control_margin
        self.design_rate = design_rate
        self.design_head = design_head
        self.sort_chart_curves_by_speed()

    def sort_chart_curves_by_speed(self):
        """Sort the curves by speed to ensure correct interpolations."""
        return sorted(self.curves, key=lambda x: x.speed)

    @property
    def min_speed(self):
        """Get the minimum speed from the curves."""
        return min(curve.speed for curve in self.curves)

    @property
    def max_speed(self):
        """Get the maximum speed from the curves."""
        return max(curve.speed for curve in self.curves)

    @property
    def speed_values(self) -> list[float]:
        return [x.speed for x in self.curves]

    @property
    def minimum_speed_curve(self) -> ChartCurve:
        return self.curves[0]

    @property
    def maximum_speed_curve(self) -> ChartCurve:
        return self.curves[-1]

    @property
    def minimum_speed(self) -> float:
        return self.minimum_speed_curve.speed

    @property
    def maximum_speed(self) -> float:
        return self.maximum_speed_curve.speed

    @property
    def minimum_rate(self) -> float:
        return np.min([x.minimum_rate for x in self.curves])

    @property
    def maximum_rate(self) -> float:
        return np.max([x.maximum_rate for x in self.curves])

    @property
    def is_100_percent_efficient(self) -> bool:
        """Check if all curves as 100 % efficient.

        Note: Only used to avoid interpolating efficiency if all values are 100%. Could probably be removed.
        """
        return np.all([x.is_100_percent_efficient for x in self.curves])

    @property
    def minimum_head_as_function_of_rate(self) -> interp1d:
        """Min head = f(rate).

        We find the minimum head as a function of rate by following the minimum speed curve and the stone wall.

        Setup a linear interpolation function for head(rate) following the rate-head for minimum speed
        and then following stone wall up to rate/head for maximum-speed.

        Note: Stone-wall is now modelled as a straight line from the maximum rate point of the minimum speed curve
            to the maximum rate point of the maximum speed curve. Consider to improve the modeling of stone-wall
            by interpolating all maximum rate points of all speeds.

        Note: We can probably skip this if-else flow since the stone wall should
            always slant with a "positive gradient" -> Keep the code within the if-statement. Remove the else-part.
            Then we should validate this in the input.

        """
        if self.maximum_speed_curve.maximum_rate > self.minimum_speed_curve.rate[-1]:
            """
            For all "normally" shaped compressor charts, the stone wall should be slanting with a positive gradient (from
            lower left to upper right), thus this right end point of the maximum speed curve should be included
            However, make the test that this point is actually to the left (higher rate value) than the minimum speed
            curve for mathematical robustness
            """
            (
                rate_at_top_of_stone_wall,
                head_at_top_of_stone_wall,
                _,
            ) = self.maximum_speed_curve.rate_head_and_efficiency_at_maximum_rate

            rate_values = np.append(self.minimum_speed_curve.rate, rate_at_top_of_stone_wall)
            head_values = np.append(self.minimum_speed_curve.head, head_at_top_of_stone_wall)

        else:
            rate_values = self.minimum_speed_curve.rate
            head_values = self.minimum_speed_curve.head

        return interp1d(
            x=rate_values,
            y=head_values,
            fill_value=(
                head_values[0],
                head_values[-1],
            ),
            bounds_error=False,
        )

    @property
    def minimum_rate_as_function_of_head(self) -> interp1d:
        """Minimum flow = f(head).

        Assumes choking.

        make a linear interpolation function rate = f(head) that follows a straight line from the minimum rate point of
        minimum and maximum speed curves respectively.

        For head values above and below minimum and maximum head defined by the input points, the function is defined
        such that the end points are extrapolated constant.
        """
        # Upper point at minimum flow line
        head_at_min_rate_at_maximum_speed = self.maximum_speed_curve.head_values[0]
        rate_at_min_rate_at_maximum_speed = self.maximum_speed_curve.rate_values[0]

        # Lower point at minimum flow line
        head_at_min_rate_at_minimum_speed = self.minimum_speed_curve.head_values[0]
        rate_at_min_rate_at_minimum_speed = self.minimum_speed_curve.rate_values[0]

        return interp1d(
            x=[head_at_min_rate_at_minimum_speed, head_at_min_rate_at_maximum_speed],
            y=[rate_at_min_rate_at_minimum_speed, rate_at_min_rate_at_maximum_speed],
            fill_value=(rate_at_min_rate_at_minimum_speed, rate_at_min_rate_at_maximum_speed),
            bounds_error=False,
        )

    @property
    def minimum_rate_as_function_of_head_no_choking(self) -> interp1d:
        """Minimum flow = f(head).

        Assumes no choking:

        Without choking, the minimum flow will follow the minimum speed curve below "control line" min flow line
        """
        # Upper point at minimum flow line
        head_at_min_rate_at_maximum_speed = self.maximum_speed_curve.head_values[0]
        rate_at_min_rate_at_maximum_speed = self.maximum_speed_curve.rate_values[0]

        # Ensure descending values in min speed heads array.
        heads_at_minimum_speed = self.minimum_speed_curve.head_values[::-1]  # reverse array
        rates_at_minimum_speed = self.minimum_speed_curve.rate_values[::-1]  # reverse array

        head_values_no_choke = list(heads_at_minimum_speed) + [head_at_min_rate_at_maximum_speed]
        volume_rate_values_no_choke = list(rates_at_minimum_speed) + [rate_at_min_rate_at_maximum_speed]
        return interp1d(
            x=head_values_no_choke,
            y=volume_rate_values_no_choke,
            bounds_error=False,
            fill_value=(
                volume_rate_values_no_choke[0],
                volume_rate_values_no_choke[-1],
            ),
        )

    @property
    def maximum_rate_as_function_of_head(self) -> interp1d:
        """Maximum rate = f(head).

        Assumes choking:
        """
        sorted_index = self.maximum_speed_curve.head_values.argsort()
        heads_at_maximum_speed = self.maximum_speed_curve.head_values[sorted_index]
        rates_at_maximum_speed = self.maximum_speed_curve.rate_values[sorted_index]

        """
        When choking is true (and thus heads below minimum will be choked up), the maximum rate is defined by the
        maximum speed head/rate points
        """
        return interp1d(
            x=heads_at_maximum_speed,
            y=rates_at_maximum_speed,
            bounds_error=False,
            fill_value=(
                rates_at_maximum_speed[0],
                rates_at_maximum_speed[-1],
            ),
        )

    @property
    def maximum_rate_as_function_of_head_no_choking(self) -> interp1d:
        """Maximum rate = f(head).

        Assumes no choking

        When choking is not true. and thus heads below minimum will not be choked up, the maximum rate is
        defined by the maximum speed head/rate points for head values above the minimum head of the maximum speed
        For head values below this, it will be defined by stone wall. The maximum rate endpoints for the various
        speed curves.
        """
        (
            min_speed_rate_at_maximum_rate,
            min_speed_head_at_maximum_rate,
            _,
        ) = self.minimum_speed_curve.rate_head_and_efficiency_at_maximum_rate

        sorted_index = self.maximum_speed_curve.head_values.argsort()
        heads_at_maximum_speed = self.maximum_speed_curve.head_values[sorted_index]
        rates_at_maximum_speed = self.maximum_speed_curve.rate_values[sorted_index]

        head_values_maximum_speed_plus_stone_wall_lower_speed_value = [min_speed_head_at_maximum_rate] + list(
            heads_at_maximum_speed
        )
        rate_values_maximum_speed_plus_stone_wall_lower_speed_value = [min_speed_rate_at_maximum_rate] + list(
            rates_at_maximum_speed
        )
        return interp1d(
            x=head_values_maximum_speed_plus_stone_wall_lower_speed_value,
            y=rate_values_maximum_speed_plus_stone_wall_lower_speed_value,
            bounds_error=False,
            fill_value=(
                rate_values_maximum_speed_plus_stone_wall_lower_speed_value[0],
                rate_values_maximum_speed_plus_stone_wall_lower_speed_value[-1],
            ),
        )

    @property
    def maximum_head_as_function_of_rate(self) -> interp1d:
        """Maximum head = f(rate)."""
        return interp1d(
            x=self.maximum_speed_curve.rate_values,
            y=self.maximum_speed_curve.head_values,
            fill_value=(self.maximum_speed_curve.head_values[0], self.maximum_speed_curve.head_values[-1]),
            bounds_error=False,
        )

    @property
    def minimum_rate_as_function_of_speed(self) -> interp1d:
        """Minimum rate = f(speed)."""
        minimum_rate_for_speed_values = [x.minimum_rate for x in self.curves]

        return interp1d(
            x=self.speed_values,
            y=minimum_rate_for_speed_values,
            bounds_error=False,
            fill_value=(
                minimum_rate_for_speed_values[0],
                minimum_rate_for_speed_values[-1],
            ),
        )

    @property
    def maximum_rate_as_function_of_speed(self) -> interp1d:
        maximum_rate_for_speed_values = [x.maximum_rate for x in self.curves]

        return interp1d(
            x=self.speed_values,
            y=maximum_rate_for_speed_values,
            bounds_error=False,
            fill_value=(
                maximum_rate_for_speed_values[0],
                maximum_rate_for_speed_values[-1],
            ),
        )

    def efficiency_as_function_of_rate_and_head(
        self,
        rates: NDArray[np.float64],
        heads: NDArray[np.float64],
    ) -> NDArray[np.float64]:
        """Calculate efficiency for rate, head points within chart capacity. For points outside capacity, one should use
        evaluate_capacity_and_extrapolate_below_minimum first to extrapolate points below asv/minimum speed first
        Outside the chart, the efficiency values will be some combination of the closes points efficiency values.

        Find the upper and lower speed curve
        Find distance to each of these and their
        efficiency at the closest point
        Set efficiency to distance averaged efficiency of these

        Note on scaling: We scale the compressor map in order to equally weigh rate and head values regardless of input
            units.

        :param rates: [Am3/h]
        :param heads: [J/kg]
        """
        # No need to calculate efficiency if all efficiencies are 100 %.
        if self.is_100_percent_efficient:
            return np.ones_like(rates)

        efficiencies = np.full_like(rates, fill_value=1.0, dtype=float)

        # Scaling the chart and input values in order to weigh rate and head equally. This makes the interpolation
        # unit-independent.
        mean_rates = np.mean([value for curve in self.curves for value in curve.rate])
        std_rates = np.std([value for curve in self.curves for value in curve.rate])
        mean_heads = np.mean([value for curve in self.curves for value in curve.head])
        std_heads = np.std([value for curve in self.curves for value in curve.head])

        # Defencive programming. If standard deviation of the chart is 0 there is probably something wrong with the
        # input in the first place. This is typically seen when generating a compressor chart during evaluation based
        # on a given efficiency + rate and heads used for evaluation. Typically, an issue when using a compressor system
        # and evaluating 0 rates or 0 heads.
        if std_rates == 0 or std_heads == 0:
            std_rates = 1
            std_heads = 1

        scaled_heads = (heads - mean_heads) / std_heads
        scaled_rates = (rates - mean_rates) / std_rates

        scaled_chart_curves = [
            # Note: the values will contain negative values which will result in a validation error unless we do this:
            ChartCurve(
                rate_actual_m3_hour=array_to_list((curve.rate_values - mean_rates) / std_rates),
                polytropic_head_joule_per_kg=array_to_list((curve.head_values - mean_heads) / std_heads),
                efficiency_fraction=curve.efficiency,
                speed_rpm=curve.speed,
            )
            for curve in self.curves
        ]
        for i, rate in enumerate(scaled_rates):
            q = rate
            h = scaled_heads[i]

            distance_above = np.inf
            distance_below = -np.inf
            efficiency_above = 1
            efficiency_below = 1

            for scaled_chart_curve in scaled_chart_curves:
                distance, efficiency = scaled_chart_curve.get_distance_and_efficiency_from_closest_point_on_curve(
                    rate=q, head=h
                )

                if 0 <= distance < distance_above:  # Curve is above this point
                    distance_above, efficiency_above = distance, efficiency
                elif distance_below < distance < 0:  # Curve is below this point
                    distance_below, efficiency_below = distance, efficiency

            alpha = self._get_alpha_from_distances(
                distance_above=distance_above,
                distance_below=distance_below,
            )

            efficiency = alpha * efficiency_below + (1.0 - alpha) * efficiency_above
            efficiencies[i] = efficiency

        return efficiencies

    @staticmethod
    def _get_alpha_from_distances(distance_above: float, distance_below: float) -> float:
        """Given a speed we interpolate a head and rate, and also between speed curves. This function calculates the shortest
        distance to the speed curve above and below. Alpha is the constant used in weighting the interpolation result.

        :param distance_above: Shortest distance to curve above
        :param distance_below: Shortest distance to curve below
        :return:
        """
        if np.isinf(distance_above):
            return 1.0
        elif np.isinf(distance_below):
            return 0.0
        else:
            return abs(distance_above) / (abs(distance_above) + abs(distance_below))

    def closest_curve_below_speed(self, speed: float) -> ChartCurve | None:
        # High to low speed -> need to reverse the original list of curves
        filtered_curves = list(filter(lambda x: x.speed <= speed, self.curves[::-1]))

        if any(filtered_curves):
            # Get the first that is the same or below given speed.
            return filtered_curves[0]
        else:
            return None

    def closest_curve_above_speed(self, speed: float) -> ChartCurve | None:
        # Low to high speed -> keep the original order of curves.
        filtered_curves = list(filter(lambda x: x.speed >= speed, self.curves))

        if any(filtered_curves):
            # Get the first that is the same or higher speed.
            return filtered_curves[0]
        else:
            return None

    def get_curve_by_speed(self, speed: float) -> ChartCurve | None:
        filtered_curves = list(filter(lambda x: x.speed == speed, self.curves))
        if any(filtered_curves):
            return filtered_curves[0]
        else:
            return None
