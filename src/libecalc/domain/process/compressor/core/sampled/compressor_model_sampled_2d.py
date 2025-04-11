import numpy as np
import pandas as pd
from numpy.typing import NDArray
from scipy.interpolate import LinearNDInterpolator, interp1d
from scipy.spatial import ConvexHull

from libecalc.domain.process.compressor.core.sampled.constants import (
    PD_NAME,
    PS_NAME,
    RATE_NAME,
)
from libecalc.domain.process.compressor.core.sampled.convex_hull_common import (
    get_lower_upper_qhull,
    sort_ndarray_by_column,
)


class CompressorModelSampled2DRatePd:
    """AKA: ChangeRateAndDischargePressureScenario.

    Compressor/Pump energy function. A) Functionality to "map" (project) from a Rate/Pd combination outside the working
    area of the compressor/pump to the combination that it will project to after ASV recycle (increase rate) and
    increased Discharge Pressure, including interpolation (barycentric (trilinear) interpolation) and B) calculate
    energy usage based on A)

    The particular Convex Hull/Gap case for the 2D case where Rate and Discharge Pressure varies, i.e. Suction Pressure
    is either A) degenerated (fixed, same value for Ps for all values of rate and Pd, and hence originally a 3D case,
    but simplified due to that fact) or B) not provided (in the compressor function)

    As for the other convex hull functions, we seek to emulate ASV (Anti Surge Valve) functionality (to increase Rate)
    and to increase the Discharge Pressure. Due to the underlying system (cheaper energywise?), the rate is first
    increased, before possibly increasing the Discharge Pressure. The rate or Pd is ONLY changed/increased if the input
    parameters are OUTSIDE the working area of the compressor.
    """

    # Need to provide which data is on which index in data frame
    rate_axis: int = 0
    pd_axis: int = 1

    # Need to provide the order of the parameters we use in dataframe
    variable_order_2d: list[str] = [RATE_NAME, PD_NAME]

    support_max_rate = True

    def __init__(self, sampled_data: pd.DataFrame, function_header: str):
        """Parameters
        ----------
        sampled_data: pandas dataframe with 3 dimensions (rate, pd and value/y)
        function_header: the key used in the dataframe for the value, provided in EcalcYamlKeywords
        """
        # the interpolator we use when calculating energy usage
        self._interpolator = LinearNDInterpolator(
            sampled_data[self.variable_order_2d][:].values,
            sampled_data[function_header[:]][:].values,
            fill_value=np.nan,
            rescale=True,
        )

        # we define a convex hull for the working area for the compressor
        # for any point (rate, Dp) in the convex hull we can draw a line between
        # them to interpolate and find interpolated values
        convex_hull = ConvexHull(sampled_data[self.variable_order_2d][:].values)

        # we can only increase rate, therefore we do not care about upper_rate_points...
        # we either want upper or lower convex hull, so for Pd we want lower
        (
            lower_rate_points_qh,
            _,
            upper_rate_monotonic_correct_points_qh,
        ) = get_lower_upper_qhull(convex_hull, axis=self.rate_axis, case_2d="rate_pd")
        lower_rate_points = lower_rate_points_qh.points
        upper_rate_monotonic_correct_points = upper_rate_monotonic_correct_points_qh.points

        lower_pd_points_qh, _, _ = get_lower_upper_qhull(convex_hull, axis=self.pd_axis)
        lower_pd_points = lower_pd_points_qh.points

        lower_rate_points_sorted = sort_ndarray_by_column(lower_rate_points, self.pd_axis)

        self._minimum_rate_function = interp1d(
            x=lower_rate_points_sorted[:, self.pd_axis],
            y=lower_rate_points_sorted[:, self.rate_axis],
            fill_value=(
                lower_rate_points_sorted[0, self.rate_axis],
                lower_rate_points_sorted[-1, self.rate_axis],
            ),
            bounds_error=False,
        )

        lower_pd_points_sorted = sort_ndarray_by_column(lower_pd_points, self.rate_axis)

        self._minimum_pd_function = interp1d(
            x=lower_pd_points_sorted[:, self.rate_axis],
            y=lower_pd_points_sorted[:, self.pd_axis],
            fill_value=(
                lower_pd_points_sorted[0, self.pd_axis],
                lower_pd_points_sorted[-1, self.pd_axis],
            ),
            bounds_error=False,
        )

        # For maximum rate
        # Why upper monotonic? and why decreasing monotonic? because we can always increase Pd, not decrease
        upper_monotonic_points_sorted = sort_ndarray_by_column(upper_rate_monotonic_correct_points, self.pd_axis)

        # create a maximum rate function for the upper monotonic points (monotonically increasing Pd, monotonically
        # decreasing rate)
        # Fill with; we can always increase Pd, so extrapolate to first rate value of monotonic list
        # We cannot decrease Pd, extrapolation after monotonic points is not possible, so then rate is not valid and
        # we set to 0. Should somehow set/indicate that 0 means invalid..and use that in general
        self._maximum_rate_function = interp1d(
            x=upper_monotonic_points_sorted[:, self.pd_axis],
            y=upper_monotonic_points_sorted[:, self.rate_axis],
            fill_value=(upper_monotonic_points_sorted[0, self.rate_axis], 0),
            bounds_error=False,
        )

        upper_monotonic_points_sorted_on_rate = sort_ndarray_by_column(
            upper_rate_monotonic_correct_points, self.rate_axis
        )
        self._maximum_pd_function = interp1d(
            x=upper_monotonic_points_sorted_on_rate[:, self.rate_axis],
            y=upper_monotonic_points_sorted_on_rate[:, self.pd_axis],
            fill_value=(
                upper_monotonic_points_sorted_on_rate[0, self.pd_axis],
                0,
            ),
            bounds_error=False,
        )

    @classmethod
    def setup_from_arrays(
        cls,
        rates: NDArray[np.float64],
        discharge_pressures: NDArray[np.float64],
        function_values: NDArray[np.float64],
    ):
        function_value_header = "function_value"
        dataframe = pd.DataFrame(
            {RATE_NAME: rates, PD_NAME: discharge_pressures, function_value_header: function_values}
        )
        return cls(sampled_data=dataframe, function_header=function_value_header)

    def evaluate(
        self, rate: NDArray[np.float64], discharge_pressure: NDArray[np.float64], **kwargs
    ) -> NDArray[np.float64]:
        """AKA: run/emulate ; returns energy consumption and possibly emission.

        For a given set of rate and pressure discharge, find the energy usage

        Parameters
        ----------
        rate
        discharge_pressure

        Returns:
        -------
        energy consumption (fuel or el)
        """
        rate_projected, pd_projected = self._project_variables_for_evaluation(
            rate=rate, discharge_pressure=discharge_pressure
        )
        x_for_interpolator = np.stack((rate_projected, pd_projected), axis=-1)
        return np.array(self._interpolator(x_for_interpolator))

    def get_max_rate(self, discharge_pressure: NDArray[np.float64]) -> float:
        """AKA: find_maximum_compatible_rate.

        For this compressor (train), find the maximum rate it can handle. If current rate > max rate for a given Pd,
        then it will have to be distributed among several compressors in parallel

        Parameters
        -----------
        discharge_pressure: discharge pressure

        Returns:
        -------
        rate: corresponding max rate for the given discharge pressure
        """
        return self._maximum_rate_function(discharge_pressure)

    def get_max_discharge_pressure(self, rate: NDArray[np.float64] | float) -> NDArray[np.float64] | float:
        if isinstance(rate, int | float):
            return float(self._maximum_pd_function(np.asarray([rate]))[0])
        return np.array(self._maximum_pd_function(rate))

    def _project_variables_for_evaluation(self, rate: NDArray[np.float64], discharge_pressure: NDArray[np.float64]):
        """AKA: make_parameters_compatible_to_compressor_working_area
        Attempt to project rate and Pd to within the convex hull working area for the compressor. If we succeed a number
        is returned within (or on the border of the convex hull), otherwise NaN.

        Parameters
        ----------
        rate
        discharge_pressure

        Returns:
        -------
        projected rate
        projected pd
        """
        # minimum we need to increase rate to
        rate_projected = np.fmax(rate, self._minimum_rate_function(discharge_pressure))

        # minimum we need to increase Pd to
        discharge_pressure_projected = np.fmax(discharge_pressure, self._minimum_pd_function(rate_projected))

        return rate_projected, discharge_pressure_projected


class CompressorModelSampled2DRatePs:
    rate_axis = 0
    ps_axis = 1

    variable_order_2d = [RATE_NAME, PS_NAME]

    support_max_rate = True

    def __init__(self, sampled_data: pd.DataFrame, function_header: str):
        self._interpolator = LinearNDInterpolator(
            sampled_data[self.variable_order_2d][:].values,
            sampled_data[function_header[:]][:].values,
            fill_value=np.nan,
            rescale=True,
        )

        convex_hull = ConvexHull(sampled_data[self.variable_order_2d][:].values)
        (
            lower_rate_points_qh,
            _,
            upper_rate_monotonic_correct_points_qh,
        ) = get_lower_upper_qhull(convex_hull, axis=self.rate_axis, case_2d="rate_ps")
        lower_rate_points = lower_rate_points_qh.points
        upper_rate_monotonic_correct_points = upper_rate_monotonic_correct_points_qh.points

        _, upper_ps_points_qh, _ = get_lower_upper_qhull(convex_hull, axis=self.ps_axis, case_2d="rate_ps")
        upper_ps_points = upper_ps_points_qh.points

        lower_rate_points_sorted = sort_ndarray_by_column(lower_rate_points, self.ps_axis)
        upper_ps_points_sorted = sort_ndarray_by_column(upper_ps_points, self.rate_axis)
        self._max_ps = lower_rate_points_sorted[-1, self.ps_axis]
        self._minimum_rate_function = interp1d(
            x=lower_rate_points_sorted[:, self.ps_axis],
            y=lower_rate_points_sorted[:, self.rate_axis],
            fill_value=(
                lower_rate_points_sorted[0, self.rate_axis],
                lower_rate_points_sorted[-1, self.rate_axis],
            ),
            bounds_error=False,
        )
        self._maximum_ps_function = interp1d(
            x=upper_ps_points_sorted[:, self.rate_axis],
            y=upper_ps_points_sorted[:, self.ps_axis],
            fill_value=(
                upper_ps_points_sorted[0, self.ps_axis],
                upper_ps_points_sorted[-1, self.ps_axis],
            ),
            bounds_error=False,
        )

        upper_monotonic_points_sorted = sort_ndarray_by_column(upper_rate_monotonic_correct_points, self.ps_axis)
        self._maximum_rate_function = interp1d(
            x=upper_monotonic_points_sorted[:, self.ps_axis],
            y=upper_monotonic_points_sorted[:, self.rate_axis],
            fill_value=(0, upper_monotonic_points_sorted[-1, self.rate_axis]),
            bounds_error=False,
        )

    def evaluate(self, rate: NDArray[np.float64], suction_pressure: NDArray[np.float64], **kwargs):
        rate_projected, ps_projected = self._project_variables_for_evaluation(rate=rate, ps=suction_pressure)
        x_for_interpolator = np.stack((rate_projected, ps_projected), axis=-1)
        energy_consumption = self._interpolator(x_for_interpolator)

        return energy_consumption

    def get_max_rate(self, ps: NDArray[np.float64]):
        return self._maximum_rate_function(ps)

    def _project_variables_for_evaluation(self, rate: NDArray[np.float64], ps: NDArray[np.float64]):
        rate_projected = np.fmax(rate, self._minimum_rate_function(ps))
        ps_projected = np.fmin(ps, self._maximum_ps_function(rate_projected))

        return rate_projected, ps_projected


class CompressorModelSampled2DPsPd:
    ps_axis = 0
    pd_axis = 1

    variable_order_2d = [PS_NAME, PD_NAME]

    support_max_rate = False

    def __init__(self, sampled_data: pd.DataFrame, function_header: str):
        self._interpolator = LinearNDInterpolator(
            sampled_data[self.variable_order_2d][:].values,
            sampled_data[function_header[:]][:].values,
            fill_value=np.nan,
            rescale=True,
        )

        convex_hull = ConvexHull(sampled_data[self.variable_order_2d][:].values)
        lower_pd_points_qh, _, _ = get_lower_upper_qhull(convex_hull, axis=self.pd_axis, case_2d="ps_pd")
        lower_pd_points = lower_pd_points_qh.points

        _, upper_ps_points_qh, _ = get_lower_upper_qhull(convex_hull, axis=self.ps_axis, case_2d="ps_pd")
        upper_ps_points = upper_ps_points_qh.points

        lower_pd_points_sorted = sort_ndarray_by_column(lower_pd_points, self.ps_axis)
        upper_ps_points_sorted = sort_ndarray_by_column(upper_ps_points, self.pd_axis)

        self._minimum_pd_function = interp1d(
            x=lower_pd_points_sorted[:, self.ps_axis],
            y=lower_pd_points_sorted[:, self.pd_axis],
            fill_value=(
                lower_pd_points_sorted[0, self.pd_axis],
                lower_pd_points_sorted[-1, self.pd_axis],
            ),
            bounds_error=False,
        )

        self._maximum_ps_function = interp1d(
            x=upper_ps_points_sorted[:, self.pd_axis],
            y=upper_ps_points_sorted[:, self.ps_axis],
            fill_value=(
                upper_ps_points_sorted[0, self.ps_axis],
                upper_ps_points_sorted[-1, self.ps_axis],
            ),
            bounds_error=False,
        )

    def evaluate(self, suction_pressure: NDArray[np.float64], discharge_pressure: NDArray[np.float64], **kwargs):
        ps_projected, pd_projected = self._project_variables_for_evaluation(ps=suction_pressure, pd=discharge_pressure)
        x_for_interpolator = np.stack((ps_projected, pd_projected), axis=-1)
        energy_consumption = self._interpolator(x_for_interpolator)

        return energy_consumption

    def get_max_rate(
        self, ps: NDArray[np.float64] | None = None, pd: NDArray[np.float64] | None = None
    ) -> NDArray[np.float64]:
        raise NotImplementedError  # Not relevant

    def _project_variables_for_evaluation(self, ps: NDArray[np.float64], pd: NDArray[np.float64]):
        pd_projected = np.fmax(pd, self._minimum_pd_function(ps))
        ps_projected = np.fmin(ps, self._maximum_ps_function(pd_projected))

        return ps_projected, pd_projected
