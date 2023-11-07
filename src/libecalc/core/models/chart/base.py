from typing import List, Optional, Tuple

import numpy as np
from numpy.typing import NDArray
from scipy.interpolate import interp1d
from shapely.geometry import LineString, Point

from libecalc import dto


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

    def __init__(self, data_transfer_object: dto.ChartCurve):
        self.data_transfer_object = data_transfer_object
        self.rate_actual_m3_hour = data_transfer_object.rate_actual_m3_hour
        self.polytropic_head_joule_per_kg = data_transfer_object.polytropic_head_joule_per_kg
        self.efficiency_fraction = data_transfer_object.efficiency_fraction
        self.speed_rpm = data_transfer_object.speed_rpm

    @property
    def rate(self) -> List[float]:
        return self.rate_actual_m3_hour

    @property
    def head(self) -> List[float]:
        return self.polytropic_head_joule_per_kg

    @property
    def efficiency(self) -> List[float]:
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
    def efficiency_values(self) -> Optional[NDArray[np.float64]]:
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
    def rate_head_and_efficiency_at_minimum_rate(self) -> Tuple[float, float, float]:
        """Return data point (rate, head, efficiency) for the minimum rate value."""
        return self.rate[0], self.head[0], self.efficiency[0]

    @property
    def rate_head_and_efficiency_at_maximum_rate(self) -> Tuple[float, float, float]:
        """Return data point (rate, head, efficiency) for the maximum rate value (Top of stone wall)."""
        return self.rate[-1], self.head[-1], self.efficiency[-1]

    def get_distance_and_efficiency_from_closest_point_on_curve(self, rate: float, head: float) -> Tuple[float, float]:
        """Compute the closest distance from a point (rate,head) to the (interpolated) curve and corresponding efficiency for
        that closest point.
        """
        head_linestring = LineString([(x, y) for x, y in zip(self.rate_values, self.head_values)])
        p = Point(rate, head)

        distance = p.distance(head_linestring)
        closest_interpolated_point = head_linestring.interpolate(head_linestring.project(p))
        if closest_interpolated_point.y < p.y:
            distance = -distance
        efficiency = float(self.efficiency_as_function_of_rate(closest_interpolated_point.x))
        return distance, efficiency
