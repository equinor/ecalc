import numpy as np
import pandas as pd
from numpy.typing import NDArray
from scipy.interpolate import LinearNDInterpolator, interp1d
from scipy.spatial import ConvexHull, Delaunay

from libecalc.common.logger import logger
from libecalc.domain.process.compressor.core.sampled.constants import (
    EPSILON,
    PD_NAME,
    PS_NAME,
    RATE_NAME,
)
from libecalc.domain.process.compressor.core.sampled.convex_hull_common import (
    HalfConvexHull,
    LinearInterpolatorSimplicesDefined,
    get_lower_upper_qhull,
    sort_ndarray_by_column,
)

EPSILON_MAX_RATE = 1e-4

# Projections - explanation of computations
# The input data, with variables rate, ps and pd and function value power or fuel
# is used to set up an interpolation function in 3D, i.e. the variables are defined
# in the 3D space (rate, ps, pd), and the input data defines function values at each
# of the input nodes. The variables in this input is enclosed by the convex hull of the
# variables.
#
# When evaluating this function for a point (rate, ps, pd) inside the convex hull,
# the LinearNDInterpolator will use barycentric interpolation and everything is ok.
# However, some points outside the convex hull should also be evaluated as
# certain extrapolations may be done to mimic anti-surge valves/recirculation and
# pressure choking.
#
# For points "under" the convex hull in the rate-direction, the rate should be projected
# up to the convex hull before evaluation (and thus evaluate to the same value as for
# the minimum rate given the corresponding pressures)
#
# For points "under" the convex hull in the pd-direction, the pd should be projected up to
# the convex hull. This is because if the pd is smaller than the minimum pd, it is assumed
# that the compressor/pump will actually pressure up to the minimum pd and the pressure
# is choked back afterwards to meet the requested pressure.
#
# For points "above" the convex hull in the ps-direction, the ps should be projected down to
# the convex hull. This is because is the ps is larger than the maximum ps, it is assumed
# that the ps is choked down to the pump/compressor minimum allowed suction pressure before
# compression.
#
# All the minimum/maximum rate/pressures above can be calculated by retrieving the lower/upper
# part of the 3d convex hull in the corresponding variable and use the variable in question as
# function value and the two remaining as variables in a 2d interpolation function.
#
# But, in order to use the 2d minimum/maximum functions, one must ensure that the remaining two
# variables are inside the (2d) convex hull of this function. If they are not, it is because the
# point to evaluate is below/above the convex hull in more than one direction. Therefore,
# the convex hull of the minimum/maximum function is also used to further find corresponding
# minimum/maximum (1d) functions for the remaining two variables. Likewise as for the full 3d
# convex hull, the upper/lower convex hulls of this 2d hull (in the direction in question) is
# computed and used for a 1d minimum/maximum function, where the direction in question represent
# the function value and the other represent the variable. Thus, to do the projection in rate direction
# from the full qhull, first pd and ps must be projected to the convex hull of the minimum rate function
# (but only project ps if larger than maximum and pd if smaller than minimum). Then the minimum rate is
# computed with the minimum rate function and the projected ps and pd as input values. The projected
# rate is set to the minimum rate if the rate is smaller than this one.
# For ps and pd, the projections are done equivalent.
#
#
# There are also projections used for computing the maximum rate for a tabular function. Then the upper
# convex hull wrt rate needs to be used. But - from the way compressors/pumps work, the maximum rate
# should be monotonically increasing when ps increases and pd decreases. However, we are not guaranteed
# this is the case from the input data, as the user may not have spanned the whole operational space.
# Thus, only the monotonic consistent part of the upper rate convex hull is used for these computations.
# Using this monotonic part of the upper rate convex hull, the computations are equivalent to the
# projections for evaluation. First ps and pd are projected with a 1d function to the convex hull of the
# maximum rate function, the maximum rate is computed for the function. The maximum rate function
# have a outside boundary value set to 0, as the maximum allowed rate for points outside the allowed
# area (too large pd or too small ps), is actually 0 - for these pressure combinations, the
# compressor/pump may not handle any rate.
#


class CompressorModelSampled3D:
    """Class to handle computation for tabular energy functions in (full, not degenerated) 3D.
    The variables are rate, ps (pressure suction) and pd (pressure discharge).
    The function value is either power or fuel.
    Compressors and pumps have operational envelopes inside which they are allowed to operate.
    These boundaries are determined for control mechanisms such as ASV (anti-surge valve) to
    ensure the rate is high enough to avoid back flow and thus destruction of the equipment
    and the flow is always above a minimum flow boundary.
    Likewise, if the compressor/pump is requested to deliver a head lower than minimum head
    (head is a function of pressure difference), what's happening is that the equipment
    operates at minimum head and then choke back the pressure either after or before the
    compressor/pump.

    For computations this means that when this function is evaluated for points outside the
    convex hull of the input variables, the point (here a point is defined as (rate, ps, pd)
    needs to be projected to the convex hull in the correct manner. To do these projections,
    functions are made when initializing the object to easily project the data at evaluation
    (or evaluation of maximum rate).

    These functions are made by calculating the lower/upper convex hull of the data, and then
    make linear interpolation functions. For example, the lower convex hull with respect to
    rate is used to make a (2d) function minimum_rate = f(ps, pd). But in order to use this
    function, one must ensure that the point to evaluate (ps,pd) in the projected [ps, pd]
    space is within the convex hull of the input data. Thus there are corresponding (1d) functions
    minimum_pd = f(ps) and maximum_ps = f(pd) functions for the minimum_rate (2d) function.

    Equivalent functions are also used for minimum_pd = f(rate, ps) and maximum_ps = f(rate, pd)
    """

    rate_axis = 0
    ps_axis = 1
    pd_axis = 2
    variable_order_3d = [RATE_NAME, PS_NAME, PD_NAME]
    support_max_rate = True

    def __init__(
        self,
        sampled_data: pd.DataFrame,
        function_header: str,
        rescale_rate: bool = True,
    ):
        logger.debug("Creating CompressorModelSampled3D")

        sampled_data_scaled = sampled_data[self.variable_order_3d].copy()
        if rescale_rate:
            self._do_rescale = True
            self._scale_factor_rate = round(
                2
                * np.average(sampled_data[RATE_NAME].values)
                / (np.average(sampled_data[PS_NAME].values) + np.average(sampled_data[PD_NAME].values))
            )
            sampled_data_scaled.loc[:, RATE_NAME] = sampled_data_scaled.loc[:, RATE_NAME] / self._scale_factor_rate
        else:
            self._do_rescale = False
            self._scale_factor_rate = 1.0

        qhull_points = sampled_data_scaled[self.variable_order_3d][:].values
        convex_hull = ConvexHull(qhull_points)
        delaunay = Delaunay(qhull_points)
        interpolator = LinearNDInterpolator(
            points=delaunay,
            values=sampled_data[function_header[:]][:].values,
            fill_value=np.nan,
            rescale=False,
        )
        self._interpolator = interpolator

        self._box_limits = {
            "min_rate": convex_hull.min_bound[self.rate_axis],
            "max_rate": convex_hull.max_bound[self.rate_axis],
            "max_ps": convex_hull.max_bound[self.ps_axis],
            "min_pd": convex_hull.min_bound[self.pd_axis],
        }

        # Setup projection functions for rate
        (
            lower_rate_qh,
            _,
            self._upper_rate_monotonic_correct_qh,
        ) = get_lower_upper_qhull(convex_hull, axis=self.rate_axis)

        # Functions used for projection for evaluation
        (
            self._lower_rate_qh_upper_ps_function,
            self._lower_rate_qh_lower_pd_function,
            self._minimum_rate_function,
        ) = _setup_minimum_rate_projection_functions(
            lower_rate_halfhull=lower_rate_qh,
            rate_axis=self.rate_axis,
            ps_axis=self.ps_axis,
            pd_axis=self.pd_axis,
        )

        self._minimum_rate_energy_function = LinearNDInterpolator(
            qhull_points[lower_rate_qh.original_qhull_indices, :][:, [self.ps_axis, self.pd_axis]],
            sampled_data[function_header[:]][lower_rate_qh.original_qhull_indices].values,
            fill_value=np.nan,
            rescale=False,
        )

        (
            self._upper_rate_qh_upper_ps_function,
            self._upper_rate_qh_lower_pd_function,
            self._maximum_rate_function,
        ) = _setup_maximum_rate_projection_functions(
            upper_rate_monotonic_halfhull=self._upper_rate_monotonic_correct_qh,
            rate_axis=self.rate_axis,
            ps_axis=self.ps_axis,
            pd_axis=self.pd_axis,
        )

        self._maximum_rate_energy_function = LinearNDInterpolator(
            points=qhull_points[self._upper_rate_monotonic_correct_qh.original_qhull_indices, :][
                :, [self.ps_axis, self.pd_axis]
            ],
            values=sampled_data[function_header[:]][
                self._upper_rate_monotonic_correct_qh.original_qhull_indices
            ].values,
            fill_value=np.nan,
            rescale=False,
        )

        # Setup projection functions for discharge pressure
        lower_pd_qh, _, _ = get_lower_upper_qhull(convex_hull, axis=self.pd_axis)

        self._minimum_pd_energy_function = LinearNDInterpolator(
            qhull_points[lower_pd_qh.original_qhull_indices, :][:, [self.rate_axis, self.ps_axis]],
            sampled_data[function_header[:]][lower_pd_qh.original_qhull_indices].values,
            fill_value=np.nan,
            rescale=False,
        )

        (
            self._lower_pd_qh_lower_rate_function,
            self._lower_pd_qh_upper_ps_function,
            self._minimum_pd_function,
        ) = _setup_minimum_pd_projection_functions(
            lower_pd_halfhull=lower_pd_qh,
            rate_axis=self.rate_axis,
            ps_axis=self.ps_axis,
            pd_axis=self.pd_axis,
        )

        # Setup projection functions for suction pressure
        _, upper_ps_qh, _ = get_lower_upper_qhull(convex_hull, axis=self.ps_axis)

        self._maximum_ps_energy_function = LinearNDInterpolator(
            qhull_points[upper_ps_qh.original_qhull_indices, :][:, [self.rate_axis, self.pd_axis]],
            sampled_data[function_header[:]][upper_ps_qh.original_qhull_indices].values,
            fill_value=np.nan,
            rescale=False,
        )

        (
            self._upper_ps_qh_lower_rate_function,
            self._upper_ps_qh_lower_pd_function,
            self._maximum_ps_function,
        ) = _setup_maximum_ps_projection_functions(
            upper_ps_halfhull=upper_ps_qh,
            rate_axis=self.rate_axis,
            ps_axis=self.ps_axis,
            pd_axis=self.pd_axis,
        )

    def get_max_rate(self, ps: NDArray[np.float64] | float, pd: NDArray[np.float64] | float):
        if self._maximum_rate_function is None:
            self._setup_projection_functions_for_max_rate()  # Todo: Define this function?

        # Project ps and pd to qhull boundary if they are outside and may be projected
        # ps may be projected downwards to qhull, pd may be projected upwards to qhull
        # Project wrt pd first (lift pd if too low)
        pd_projected = np.fmax(pd, self._upper_rate_qh_lower_pd_function(ps))
        ps_projected = np.fmin(ps, self._upper_rate_qh_upper_ps_function(pd_projected))

        max_rates = self._maximum_rate_function(np.column_stack((ps_projected, pd_projected)))  # type: ignore[misc]

        if self._do_rescale:
            max_rates = max_rates * self._scale_factor_rate

        return max_rates

    def evaluate(
        self,
        rate: NDArray[np.float64],
        suction_pressure: NDArray[np.float64],
        discharge_pressure: NDArray[np.float64],
        **kwargs,
    ):
        rate_scaled = rate / self._scale_factor_rate if self._do_rescale else rate

        x_for_interpolator = _convert_variables_for_interpolator(
            rate=rate_scaled, suction_pressure=suction_pressure, discharge_pressure=discharge_pressure
        )
        energy_consumption = self._interpolator(x_for_interpolator)

        nan_value_indices = np.argwhere(np.isnan(energy_consumption))[:, 0]
        energy_consumption[nan_value_indices] = self._project_and_calculate_outsiders_rate(
            rate=rate_scaled[nan_value_indices],
            suction_pressure=suction_pressure[nan_value_indices],
            discharge_pressure=discharge_pressure[nan_value_indices],
        )
        nan_value_indices = nan_value_indices[np.argwhere(np.isnan(energy_consumption[nan_value_indices]))[:, 0]]
        energy_consumption[nan_value_indices] = self._project_and_calculate_outsiders_pd(
            rate=rate_scaled[nan_value_indices],
            suction_pressure=suction_pressure[nan_value_indices],
            discharge_pressure=discharge_pressure[nan_value_indices],
        )

        nan_value_indices = nan_value_indices[np.argwhere(np.isnan(energy_consumption[nan_value_indices]))[:, 0]]
        energy_consumption[nan_value_indices] = self._project_and_calculate_outsiders_ps(
            rate=rate_scaled[nan_value_indices],
            suction_pressure=suction_pressure[nan_value_indices],
            discharge_pressure=discharge_pressure[nan_value_indices],
        )

        return energy_consumption

    def _project_variables_for_evaluation(
        self, rate: NDArray[np.float64], suction_pressure: NDArray[np.float64], discharge_pressure: NDArray[np.float64]
    ):
        """Project rate, suction pressure (ps) and discharge pressure (pd) given in x
        to the 3D convex hull of the points in lower_rate_points for ps larger than
        the given points and for rates and pd smaller than the given points. This mimics
        what happens when a compressor/pump are requested to handle input (rate,ps,pd)
        points which are outside the operational area, but which are handled by
        ASV/recirculation and pressure choking.
        """
        rate, suction_pressure, discharge_pressure = _project_on_rate(
            lower_rate_qh_lower_pd_function=self._lower_rate_qh_lower_pd_function,
            lower_rate_qh_upper_ps_function=self._lower_rate_qh_upper_ps_function,
            minimum_rate_function=self._minimum_rate_function,
            rate=rate,
            suction_pressure=suction_pressure,
            discharge_pressure=discharge_pressure,
        )

        rate, suction_pressure, discharge_pressure = _project_on_pd(
            lower_pd_qh_lower_rate_function=self._lower_pd_qh_lower_rate_function,
            lower_pd_qh_upper_ps_function=self._lower_pd_qh_upper_ps_function,
            minimum_pd_function=self._minimum_pd_function,
            rate=rate,
            suction_pressure=suction_pressure,
            discharge_pressure=discharge_pressure,
        )

        rate, suction_pressure, discharge_pressure = _project_on_ps(
            upper_ps_qh_lower_rate_function=self._upper_ps_qh_lower_rate_function,
            upper_ps_qh_lower_pd_function=self._upper_ps_qh_lower_pd_function,
            maximum_ps_function=self._maximum_ps_function,
            rate=rate,
            suction_pressure=suction_pressure,
            discharge_pressure=discharge_pressure,
        )

        return rate, suction_pressure, discharge_pressure

    def _project_and_calculate_outsiders_rate(
        self, rate: NDArray[np.float64], suction_pressure: NDArray[np.float64], discharge_pressure: NDArray[np.float64]
    ):
        # Find indices where rates are below minimum rates
        # and use minimum_rate_energy_function to evaluate
        # these points (projecting to full convex hull may
        # result in projected point still outside due to
        # numerical errors
        ps_projected, pd_projected, minimum_rates = _get_minimum_rates(
            lower_rate_qh_lower_pd_function=self._lower_rate_qh_lower_pd_function,
            lower_rate_qh_upper_ps_function=self._lower_rate_qh_upper_ps_function,
            minimum_rate_function=self._minimum_rate_function,
            suction_pressure=suction_pressure,
            discharge_pressure=discharge_pressure,
        )

        numerical_uncertainty_factor = (self._box_limits["max_rate"] - self._box_limits["min_rate"]) * EPSILON_MAX_RATE

        indices_rates_below_minimum = np.argwhere(rate <= minimum_rates + numerical_uncertainty_factor)[:, 0]
        energy_consumption = np.full(rate.size, np.nan)
        energy_consumption[indices_rates_below_minimum] = self._minimum_rate_energy_function(
            ps_projected[indices_rates_below_minimum],
            pd_projected[indices_rates_below_minimum],
        )

        # Find indices where the rates are above, but very close to maximum
        # and evaluate with maximum rate energy function
        # To make robust wrt numerical errors (in e.g. max rate calculations)
        ps_projected, pd_projected, maximum_rates = _get_maximum_rates(
            upper_rate_qh_lower_pd_function=self._upper_rate_qh_lower_pd_function,
            upper_rate_qh_upper_ps_function=self._upper_rate_qh_upper_ps_function,
            maximum_rate_function=self._maximum_rate_function,
            suction_pressure=suction_pressure,
            discharge_pressure=discharge_pressure,
        )
        indices_rates_close_to_maximum = np.argwhere(np.abs(rate - maximum_rates) < numerical_uncertainty_factor)[:, 0]
        energy_consumption[indices_rates_close_to_maximum] = self._maximum_rate_energy_function(
            ps_projected[indices_rates_close_to_maximum],
            pd_projected[indices_rates_close_to_maximum],
        )

        return energy_consumption

    def _project_and_calculate_outsiders_pd(
        self, rate: NDArray[np.float64], suction_pressure: NDArray[np.float64], discharge_pressure: NDArray[np.float64]
    ):
        # Find indices where discharge pressures are below minimum
        # and use minimum_pd_energy_function to evaluate
        # these points (projecting to full convex hull may
        # result in projected point still outside due to
        # numerical errors
        ps_projected, rate_projected, minimum_pd = _get_minimum_pd(
            lower_pd_qh_lower_rate_function=self._lower_pd_qh_lower_rate_function,
            lower_pd_qh_upper_ps_function=self._lower_pd_qh_upper_ps_function,
            minimum_pd_function=self._minimum_pd_function,
            rate=rate,
            suction_pressure=suction_pressure,
        )

        indices_pd_below_minimum = np.argwhere(discharge_pressure <= minimum_pd)[:, 0]
        energy_consumption = np.full(rate.size, np.nan)
        energy_consumption[indices_pd_below_minimum] = self._minimum_pd_energy_function(
            ps_projected[indices_pd_below_minimum],
            rate_projected[indices_pd_below_minimum],
        )

        return energy_consumption

    def _project_and_calculate_outsiders_ps(
        self, rate: NDArray[np.float64], suction_pressure: NDArray[np.float64], discharge_pressure: NDArray[np.float64]
    ):
        # Find indices where suction pressyres are above maximum
        # and use maximum_ps_energy_function to evaluate
        # these points (projecting to full convex hull may
        # result in projected point still outside due to
        # numerical errors
        rate_projected, pd_projected, maximum_ps = _get_maximum_ps(
            upper_ps_qh_lower_rate_function=self._upper_ps_qh_lower_rate_function,
            upper_ps_qh_lower_pd_function=self._upper_ps_qh_lower_pd_function,
            maximum_ps_function=self._maximum_ps_function,
            rate=rate,
            discharge_pressure=discharge_pressure,
        )

        indices_ps_above_maximum = np.argwhere(suction_pressure >= maximum_ps)[:, 0]
        energy_consumption = np.full(rate.size, np.nan)
        energy_consumption[indices_ps_above_maximum] = self._maximum_ps_energy_function(
            rate_projected[indices_ps_above_maximum],
            pd_projected[indices_ps_above_maximum],
        )

        return energy_consumption


def _convert_variables_for_interpolator(
    rate: NDArray[np.float64], suction_pressure: NDArray[np.float64], discharge_pressure: NDArray[np.float64]
) -> NDArray[np.float64]:
    """Join a sequence of arrays along the last axis.

    Args:
        rate:
        suction_pressure:
        discharge_pressure:

    Returns:
        Array with one interpolation point per row
    """
    return np.stack((rate, suction_pressure, discharge_pressure), axis=-1)


def _get_maximum_rates(
    upper_rate_qh_lower_pd_function: interp1d,
    upper_rate_qh_upper_ps_function: interp1d,
    maximum_rate_function: LinearInterpolatorSimplicesDefined,
    suction_pressure: NDArray[np.float64],
    discharge_pressure: NDArray[np.float64],
):
    pd_projected = np.fmax(discharge_pressure, upper_rate_qh_lower_pd_function(suction_pressure))
    ps_projected = np.fmin(suction_pressure, upper_rate_qh_upper_ps_function(pd_projected))
    maximum_rates = maximum_rate_function(ps_projected, pd_projected)

    return ps_projected, pd_projected, maximum_rates


def _get_minimum_rates(
    lower_rate_qh_lower_pd_function: interp1d,
    lower_rate_qh_upper_ps_function: interp1d,
    minimum_rate_function: LinearInterpolatorSimplicesDefined,
    suction_pressure: NDArray[np.float64] | list[float],
    discharge_pressure: NDArray[np.float64] | list[float],
) -> tuple[NDArray[np.float64], NDArray[np.float64], LinearInterpolatorSimplicesDefined]:
    pd_projected = np.fmax(discharge_pressure, lower_rate_qh_lower_pd_function(suction_pressure))
    ps_projected = np.fmin(suction_pressure, lower_rate_qh_upper_ps_function(pd_projected))
    minimum_rates = minimum_rate_function(ps_projected, pd_projected)

    return ps_projected, pd_projected, minimum_rates


def _get_maximum_ps(
    upper_ps_qh_lower_rate_function: interp1d,
    upper_ps_qh_lower_pd_function: interp1d,
    maximum_ps_function: LinearInterpolatorSimplicesDefined,
    rate: NDArray[np.float64],
    discharge_pressure: NDArray[np.float64],
):
    rate_projected = np.fmax(rate, upper_ps_qh_lower_rate_function(discharge_pressure))
    pd_projected = np.fmax(discharge_pressure, upper_ps_qh_lower_pd_function(rate_projected))
    maximum_ps = maximum_ps_function(rate_projected, pd_projected)

    return rate_projected, pd_projected, maximum_ps


def _get_minimum_pd(
    lower_pd_qh_lower_rate_function: interp1d,
    lower_pd_qh_upper_ps_function: interp1d,
    minimum_pd_function: LinearInterpolatorSimplicesDefined,
    rate: NDArray[np.float64],
    suction_pressure: NDArray[np.float64],
):
    """Function which projects an input point (rate, ps, pd) according to ASV and choking
    mechanisms. The main projection is wrt discharge pressure.
    """
    rate_projected = np.fmax(rate, lower_pd_qh_lower_rate_function(suction_pressure))
    ps_projected = np.fmin(suction_pressure, lower_pd_qh_upper_ps_function(rate_projected))
    minimum_pd = minimum_pd_function(rate_projected, ps_projected)

    return rate_projected, ps_projected, minimum_pd


def _project_on_rate(
    lower_rate_qh_lower_pd_function: interp1d,
    lower_rate_qh_upper_ps_function: interp1d,
    minimum_rate_function: LinearInterpolatorSimplicesDefined,
    rate: NDArray[np.float64],
    suction_pressure: NDArray[np.float64],
    discharge_pressure: NDArray[np.float64],
):
    """Function which projects an input point (rate, ps, pd) according to ASV and choking
    mechanisms. The main projection is wrt rate.
    """
    # Project pd and ps to convex hull of minimum_rate function (if allowed)
    # Add/subtract EPSILON to avoid numerical machine precision errors to
    # allow points to be "just outside" convex hull of interpolation function
    # and thus return undefined value.
    pd_projected = np.fmax(discharge_pressure, lower_rate_qh_lower_pd_function(suction_pressure))
    ps_projected = np.fmin(suction_pressure, lower_rate_qh_upper_ps_function(pd_projected))
    rate_projected = np.fmax(rate, minimum_rate_function(ps_projected, pd_projected) + EPSILON)

    return rate_projected, ps_projected, pd_projected


def _project_on_pd(
    lower_pd_qh_lower_rate_function: interp1d,
    lower_pd_qh_upper_ps_function: interp1d,
    minimum_pd_function: LinearInterpolatorSimplicesDefined,
    rate: NDArray[np.float64],
    suction_pressure: NDArray[np.float64],
    discharge_pressure: NDArray[np.float64],
):
    """Function which projects an input point (rate, ps, pd) according to ASV and choking
    mechanisms. The main projection is wrt discharge pressure.
    """
    rate_projected = np.fmax(rate, lower_pd_qh_lower_rate_function(suction_pressure))
    ps_projected = np.fmin(suction_pressure, lower_pd_qh_upper_ps_function(rate_projected))
    pd_projected = np.fmax(discharge_pressure, minimum_pd_function(rate_projected, ps_projected) + EPSILON)

    return rate_projected, ps_projected, pd_projected


def _project_on_ps(
    upper_ps_qh_lower_rate_function: interp1d,
    upper_ps_qh_lower_pd_function: interp1d,
    maximum_ps_function: LinearInterpolatorSimplicesDefined,
    rate: NDArray[np.float64],
    suction_pressure: NDArray[np.float64],
    discharge_pressure: NDArray[np.float64],
):
    """Function which projects an input point (rate, ps, pd) according to ASV and choking
    mechanisms. The main projection is wrt suction pressure.
    """
    rate_projected = np.fmax(rate, upper_ps_qh_lower_rate_function(discharge_pressure))
    pd_projected = np.fmax(discharge_pressure, upper_ps_qh_lower_pd_function(rate_projected))
    ps_projected = np.fmin(suction_pressure, maximum_ps_function(rate_projected, pd_projected) - EPSILON)

    return rate_projected, ps_projected, pd_projected


def _setup_minimum_rate_projection_functions(
    lower_rate_halfhull: HalfConvexHull,
    rate_axis: int = 0,
    ps_axis: int = 1,
    pd_axis: int = 2,
):
    """Function which returns functions to be used for computations of the minimum rate
    for a given (suction pressure, discharge pressure) point.
    These are to be used to set the actual rate to minimum flow rate if the rate is
    below this value to mimic anti-surve/recirculation.
    """
    if not isinstance(lower_rate_halfhull, HalfConvexHull):
        msg = "lower_rate_halfhull is not of type HalfConvexHull"
        logger.error(msg)
        raise TypeError(msg)

    lower_rate_points = lower_rate_halfhull.points

    non_rate_axes = [ps_axis, pd_axis]
    ps_axis_2d = 0 if ps_axis < pd_axis else 1
    pd_axis_2d = 1 if ps_axis < pd_axis else 0

    # For rate projection
    lower_rate_qh = ConvexHull(lower_rate_points[:, non_rate_axes])
    # qh contains ps (axis 0) and pd (axis 1)
    lower_rate_qh_lower_pd_qh, _, _ = get_lower_upper_qhull(lower_rate_qh, axis=pd_axis_2d)
    lower_rate_qh_lower_pd_points = lower_rate_qh_lower_pd_qh.points

    _, lower_rate_qh_upper_ps_qh, _ = get_lower_upper_qhull(lower_rate_qh, axis=ps_axis_2d)
    lower_rate_qh_upper_ps_points = lower_rate_qh_upper_ps_qh.points

    lower_rate_qh_lower_pd_points_sorted = sort_ndarray_by_column(
        arr=lower_rate_qh_lower_pd_points, column_index=ps_axis_2d
    )
    lower_rate_qh_upper_ps_points_sorted = sort_ndarray_by_column(
        arr=lower_rate_qh_upper_ps_points, column_index=pd_axis_2d
    )

    lower_rate_qh_lower_pd_function = interp1d(
        x=lower_rate_qh_lower_pd_points_sorted[:, ps_axis_2d],
        y=lower_rate_qh_lower_pd_points_sorted[:, pd_axis_2d],
        fill_value=(
            lower_rate_qh_lower_pd_points_sorted[0, pd_axis_2d],
            lower_rate_qh_lower_pd_points_sorted[-1, pd_axis_2d],
        ),
        bounds_error=False,
    )

    lower_rate_qh_upper_ps_function = interp1d(
        x=lower_rate_qh_upper_ps_points_sorted[:, pd_axis_2d],
        y=lower_rate_qh_upper_ps_points_sorted[:, ps_axis_2d],
        fill_value=(
            lower_rate_qh_upper_ps_points_sorted[0, ps_axis_2d],
            lower_rate_qh_upper_ps_points_sorted[-1, ps_axis_2d],
        ),
        bounds_error=False,
    )

    """
    # LinearNDInterpolator will not keep simplices from origin qhull
    # New triangulation will potentially give wrong minimum values

    Order of evaluation variables in LinearInterpolatorSimplicesDefined is defined by non_rate_axes
    while function value is defined by rate_axis, consistent with input variables rate_axis, ps_axis and pd_axis
    Make HalfConvexHull object corresponding with these for input to LinearInterpolatorSimplicesDefined
    """

    lower_rate_halfhull_reordered = lower_rate_halfhull.reorder_axes(axis=rate_axis, variable_axes=non_rate_axes)
    minimum_rate_function = LinearInterpolatorSimplicesDefined(
        half_convex_hull=lower_rate_halfhull_reordered, fill_value=0.0
    )

    return (
        lower_rate_qh_upper_ps_function,
        lower_rate_qh_lower_pd_function,
        minimum_rate_function,
    )


def _setup_minimum_pd_projection_functions(
    lower_pd_halfhull: HalfConvexHull,
    rate_axis: int = 0,
    ps_axis: int = 1,
    pd_axis: int = 2,
) -> tuple[interp1d, interp1d, LinearInterpolatorSimplicesDefined]:
    """Function which returns functions to be used for computations of the minimum
    discharge pressure for a given (rate, suction pressure) point.
    These are to be used to set the actual discharge pressure to minimum discharge
    pressure if this is below this value to mimic choking of discharge when the
    requested head is too small.
    """
    if not isinstance(lower_pd_halfhull, HalfConvexHull):
        raise TypeError("lower_pd_halfhull is not of type HalfConvexHull")

    lower_pd_points = lower_pd_halfhull.points

    non_pd_axes = [rate_axis, ps_axis]
    rate_axis_2d = 0 if rate_axis < ps_axis else 1
    ps_axis_2d = 1 if rate_axis < ps_axis else 0

    lower_pd_qh = ConvexHull(lower_pd_points[:, non_pd_axes])
    # qh contains rate and ps
    lower_pd_qh_lower_rate_qh, _, _ = get_lower_upper_qhull(lower_pd_qh, axis=rate_axis_2d)
    lower_pd_qh_lower_rate_points = lower_pd_qh_lower_rate_qh.points

    _, lower_pd_qh_upper_ps_qh, _ = get_lower_upper_qhull(lower_pd_qh, axis=ps_axis_2d)
    lower_pd_qh_upper_ps_points = lower_pd_qh_upper_ps_qh.points

    lower_pd_qh_lower_rate_points_sorted = sort_ndarray_by_column(
        arr=lower_pd_qh_lower_rate_points, column_index=ps_axis_2d
    )
    lower_pd_qh_upper_ps_points_sorted = sort_ndarray_by_column(
        arr=lower_pd_qh_upper_ps_points, column_index=rate_axis_2d
    )
    lower_pd_qh_lower_rate_function = interp1d(
        x=lower_pd_qh_lower_rate_points_sorted[:, ps_axis_2d],
        y=lower_pd_qh_lower_rate_points_sorted[:, rate_axis_2d],
        fill_value=(
            lower_pd_qh_lower_rate_points_sorted[0, rate_axis_2d],
            lower_pd_qh_lower_rate_points_sorted[-1, rate_axis_2d],
        ),
        bounds_error=False,
    )
    lower_pd_qh_upper_ps_function = interp1d(
        x=lower_pd_qh_upper_ps_points_sorted[:, rate_axis_2d],
        y=lower_pd_qh_upper_ps_points_sorted[:, ps_axis_2d],
        fill_value=(
            lower_pd_qh_upper_ps_points_sorted[0, ps_axis_2d],
            lower_pd_qh_upper_ps_points_sorted[-1, ps_axis_2d],
        ),
        bounds_error=False,
    )

    """
    # LinearNDInterpolator will not keep simplices from origin qhull
    # New triangulation will potentially give wrong minimum values

    Order of evaluation variables in LinearInterpolatorSimplicesDefined is defined by non_rate_axes
    while function value is defined by rate_axis, consistent with input variables rate_axis, ps_axis and pd_axis
    Make HalfConvexHull object corresponding with these for input to LinearInterpolatorSimplicesDefined
    """

    lower_pd_halfhull_reordered = lower_pd_halfhull.reorder_axes(axis=pd_axis, variable_axes=non_pd_axes)
    minimum_pd_function = LinearInterpolatorSimplicesDefined(
        half_convex_hull=lower_pd_halfhull_reordered, fill_value=0.0
    )

    return (
        lower_pd_qh_lower_rate_function,
        lower_pd_qh_upper_ps_function,
        minimum_pd_function,
    )


def _setup_maximum_ps_projection_functions(
    upper_ps_halfhull: HalfConvexHull,
    rate_axis: int = 0,
    ps_axis: int = 1,
    pd_axis: int = 2,
):
    """Function which returns functions to be used for computations of the maximum
    suction pressure for a given (rate, discharge pressure) point.
    These are to be used to set the actual suction pressure to maximum suction
    pressure if this is above this value to mimic choking of suction pressure when
    the requested head is too small.
    """
    if not isinstance(upper_ps_halfhull, HalfConvexHull):
        msg = "upper_ps_halfhull is not of type HalfConvexHull"
        logger.error(msg)
        raise TypeError()
    upper_ps_points = upper_ps_halfhull.points

    non_ps_axes = [rate_axis, pd_axis]
    rate_axis_2d = 0 if rate_axis < pd_axis else 1
    pd_axis_2d = 1 if rate_axis < pd_axis else 0

    upper_ps_qh = ConvexHull(upper_ps_points[:, non_ps_axes])
    # qh contains rate (axis 0) and pd (axis 1)
    upper_ps_qh_lower_rate_qh, _, _ = get_lower_upper_qhull(upper_ps_qh, axis=rate_axis_2d)
    upper_ps_qh_lower_rate_points = upper_ps_qh_lower_rate_qh.points

    upper_ps_qh_lower_pd_qh, _, _ = get_lower_upper_qhull(upper_ps_qh, axis=pd_axis_2d)
    upper_ps_qh_lower_pd_points = upper_ps_qh_lower_pd_qh.points

    upper_ps_qh_lower_rate_points_sorted = sort_ndarray_by_column(
        arr=upper_ps_qh_lower_rate_points, column_index=pd_axis_2d
    )
    upper_ps_qh_lower_pd_points_sorted = sort_ndarray_by_column(
        arr=upper_ps_qh_lower_pd_points, column_index=rate_axis_2d
    )

    upper_ps_qh_lower_rate_function = interp1d(
        x=upper_ps_qh_lower_rate_points_sorted[:, pd_axis_2d],
        y=upper_ps_qh_lower_rate_points_sorted[:, rate_axis_2d],
        fill_value=(
            upper_ps_qh_lower_rate_points_sorted[0, rate_axis_2d],
            upper_ps_qh_lower_rate_points_sorted[-1, rate_axis_2d],
        ),
        bounds_error=False,
    )
    upper_ps_qh_lower_pd_function = interp1d(
        x=upper_ps_qh_lower_pd_points_sorted[:, rate_axis_2d],
        y=upper_ps_qh_lower_pd_points_sorted[:, pd_axis_2d],
        fill_value=(
            upper_ps_qh_lower_pd_points_sorted[0, pd_axis_2d],
            upper_ps_qh_lower_pd_points_sorted[-1, pd_axis_2d],
        ),
        bounds_error=False,
    )

    upper_ps_halfhull_reordered = upper_ps_halfhull.reorder_axes(axis=ps_axis, variable_axes=non_ps_axes)
    maximum_ps_function = LinearInterpolatorSimplicesDefined(
        half_convex_hull=upper_ps_halfhull_reordered, fill_value=np.inf
    )

    return (
        upper_ps_qh_lower_rate_function,
        upper_ps_qh_lower_pd_function,
        maximum_ps_function,
    )


def _setup_maximum_rate_projection_functions(
    upper_rate_monotonic_halfhull: HalfConvexHull,
    rate_axis: int = 0,
    ps_axis: int = 1,
    pd_axis: int = 2,
):
    """Function which returns functions to be used for computations of the maximum rate
    for a given (suction pressure, discharge pressure) point.
    These are to be used to compute the maximum rate needed when the consumer system
    cross over functionality is used as one then needs to know the consumers maximum rate
    This is to mimic that the consumer will be operated at maximum rate, while the excess
    rate is transferred to another consumer.
    """
    if not isinstance(upper_rate_monotonic_halfhull, HalfConvexHull):
        msg = "upper_rate_monotonic_halfhull is not of type HalfConvexHull"
        logger.error(msg)
        raise TypeError(msg)

    upper_rate_monotonic_points = upper_rate_monotonic_halfhull.points

    non_rate_axes = [axis for axis in range(3) if axis != rate_axis]
    ps_axis_2d = 0 if ps_axis < pd_axis else 1
    pd_axis_2d = 1 if ps_axis < pd_axis else 0

    upper_rate_qh = ConvexHull(upper_rate_monotonic_points[:, non_rate_axes])

    upper_rate_qh_lower_pd_qh, _, _ = get_lower_upper_qhull(upper_rate_qh, axis=pd_axis_2d)
    upper_rate_qh_lower_pd_points = upper_rate_qh_lower_pd_qh.points

    _, upper_rate_qh_upper_ps_qh, _ = get_lower_upper_qhull(upper_rate_qh, axis=ps_axis_2d)
    upper_rate_qh_upper_ps_points = upper_rate_qh_upper_ps_qh.points

    # Sort to ensure correct fill values
    upper_rate_qh_lower_pd_points_sorted = sort_ndarray_by_column(
        arr=upper_rate_qh_lower_pd_points, column_index=pd_axis_2d
    )
    upper_rate_qh_upper_ps_points_sorted = sort_ndarray_by_column(
        arr=upper_rate_qh_upper_ps_points, column_index=ps_axis_2d
    )
    # Projection functions
    upper_rate_qh_lower_pd_function = interp1d(
        x=upper_rate_qh_lower_pd_points_sorted[:, ps_axis_2d],
        y=upper_rate_qh_lower_pd_points_sorted[:, pd_axis_2d],
        fill_value=(
            upper_rate_qh_lower_pd_points_sorted[0, pd_axis_2d],
            upper_rate_qh_lower_pd_points_sorted[-1, pd_axis_2d],
        ),
        bounds_error=False,
    )
    upper_rate_qh_upper_ps_function = interp1d(
        x=upper_rate_qh_upper_ps_points_sorted[:, pd_axis_2d],
        y=upper_rate_qh_upper_ps_points_sorted[:, ps_axis_2d],
        fill_value=(
            upper_rate_qh_upper_ps_points_sorted[0, ps_axis_2d],
            upper_rate_qh_upper_ps_points_sorted[-1, ps_axis_2d],
        ),
        bounds_error=False,
    )

    upper_rate_monotonic_halfhull_reordered = upper_rate_monotonic_halfhull.reorder_axes(
        axis=rate_axis, variable_axes=non_rate_axes
    )

    maximum_rate_function = LinearInterpolatorSimplicesDefined(
        half_convex_hull=upper_rate_monotonic_halfhull_reordered,
        fill_value=0.0,
    )

    return (
        upper_rate_qh_upper_ps_function,
        upper_rate_qh_lower_pd_function,
        maximum_rate_function,
    )
