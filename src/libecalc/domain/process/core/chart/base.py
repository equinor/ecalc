from copy import deepcopy
from typing import Self

import numpy as np
from numpy.typing import NDArray
from scipy.interpolate import interp1d
from shapely.geometry import LineString, Point

from libecalc.common.serializable_chart import ChartCurveDTO


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

    def __init__(self, data_transfer_object: ChartCurveDTO):
        self.data_transfer_object = data_transfer_object
        self.rate_actual_m3_hour = data_transfer_object.rate_actual_m3_hour
        self.polytropic_head_joule_per_kg = data_transfer_object.polytropic_head_joule_per_kg
        self.efficiency_fraction = data_transfer_object.efficiency_fraction
        self.speed_rpm = data_transfer_object.speed_rpm

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
