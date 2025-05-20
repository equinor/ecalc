import numpy as np
from numpy.typing import NDArray
from scipy.interpolate import interp1d

from libecalc.common.list.list_utils import array_to_list
from libecalc.common.serializable_chart import VariableSpeedChartDTO
from libecalc.domain.process.chart.base import ChartCurve


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

    def __init__(self, data_transfer_object: VariableSpeedChartDTO):
        self.data_transfer_object = data_transfer_object
        self.curves = [ChartCurve(curve) for curve in data_transfer_object.curves]

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
            curve.data_transfer_object.model_copy(
                update={
                    "rate_actual_m3_hour": array_to_list((curve.rate_values - mean_rates) / std_rates),
                    "polytropic_head_joule_per_kg": array_to_list((curve.head_values - mean_heads) / std_heads),
                }
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
                distance, efficiency = ChartCurve(
                    scaled_chart_curve
                ).get_distance_and_efficiency_from_closest_point_on_curve(rate=q, head=h)

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
