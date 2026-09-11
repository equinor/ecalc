"""Dependency-free reimplementation of the legacy sampled compressor model:
interpolating energy usage (and, optionally, power) from a table of sampled points
over rate, suction pressure (ps), and/or discharge pressure (pd), with any input(s)
missing or degenerate (constant across the table) simply dropped from the model.

Depending on how many of (rate, ps, pd) actually vary in the sample data, evaluation
is delegated to a 1D, 2D, or 3D interpolator (SampledCompressor1D/2D/3D) built by the
public entry point, SampledCompressor. The 2D/3D interpolators also need to
extrapolate outside the convex hull of the sample points (e.g. below the minimum
rate, or above the maximum rate) - see libecalc.energy.models.convex_hull for the shared
geometry that makes this possible, and the "ASV/choke boundary and surface
projection helpers" section below for how it's used here specifically.

Reimplements, without any dependency on libecalc.domain, the model classes from
libecalc.domain.process.compressor.core.sampled: CompressorModelSampled (as
SampledCompressor), CompressorModelSampled1D (as SampledCompressor1D),
CompressorModelSampled2DRatePs/RatePd/PsPd (as SampledCompressor2D), and
CompressorModelSampled3D (as SampledCompressor3D).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, cast

import numpy as np
from numpy.typing import NDArray
from scipy.interpolate import LinearNDInterpolator, interp1d
from scipy.spatial import ConvexHull, Delaunay

from libecalc.common.errors.ecalc_validation_error import (
    ProcessEqualLengthValidationException,
    ProcessMissingVariableValidationException,
    ProcessNegativeValuesValidationException,
)
from libecalc.common.errors.exceptions import IllegalStateException, InvalidColumnException
from libecalc.energy.models.convex_hull import (
    FloatArray,
    HalfConvexHull,
    LinearSurfaceInterpolator,
    get_lower_upper_qhull,
    sort_ndarray_by_column,
)

EPSILON = 1e-15
EPSILON_MAX_RATE = 1e-4
RATE_NAME = "RATE"
PS_NAME = "SUCTION_PRESSURE"
PD_NAME = "DISCHARGE_PRESSURE"

VariableName = Literal["RATE", "SUCTION_PRESSURE", "DISCHARGE_PRESSURE"]


@dataclass(frozen=True)
class SampledCompressorResult:
    """The result of one SampledCompressor.evaluate() query."""

    energy_usage: float
    power: float | None = None


def _as_float_array(values: list[float] | NDArray[np.float64]) -> FloatArray:
    return np.asarray(values, dtype=np.float64)


def _evaluate_interp1d(function: interp1d, value: float) -> float:
    return float(np.asarray(function(np.asarray([value], dtype=np.float64)), dtype=np.float64)[0])


def _evaluate_nd_interpolator(function: LinearNDInterpolator, coordinates: list[float]) -> float:
    return float(np.asarray(function(np.asarray([coordinates], dtype=np.float64)), dtype=np.float64)[0])


def _evaluate_surface(function: LinearSurfaceInterpolator, coordinates: list[float]) -> float:
    return float(np.asarray(function(np.asarray([coordinates], dtype=np.float64)), dtype=np.float64)[0])


def _scalar_fmax(left: float, right: float) -> float:
    if math.isnan(left):
        return right
    if math.isnan(right):
        return left
    return max(left, right)


def _scalar_fmin(left: float, right: float) -> float:
    if math.isnan(left):
        return right
    if math.isnan(right):
        return left
    return min(left, right)


# --- Begin ASV/choke boundary and surface projection helpers ---------------------
#
# Used only by SampledCompressor2D and SampledCompressor3D to extrapolate outside the
# convex hull of the sampled data: points below the minimum rate are projected onto the
# ASV (anti-surge valve recirculation) boundary, and points above the maximum rate, above
# the maximum suction pressure, or below the minimum discharge pressure are projected onto
# the choke boundary. Reimplements the corresponding boundary-setup and projection logic
# in legacy compressor_model_sampled_2d.py and compressor_model_sampled_3d.py.


@dataclass(frozen=True)
class _Boundary1D:
    """A 1D interpolated limit (e.g. minimum rate as a function of pd) used to clamp one
    coordinate of a point to the sampled data's lower/upper boundary in that direction."""

    input_axis: int
    output_axis: int
    kind: Literal["lower", "upper"]
    function: interp1d

    def apply(self, coordinates: list[float]) -> None:
        bound = _evaluate_interp1d(self.function, coordinates[self.input_axis])
        if self.kind == "lower":
            coordinates[self.output_axis] = _scalar_fmax(coordinates[self.output_axis], bound)
        else:
            coordinates[self.output_axis] = _scalar_fmin(coordinates[self.output_axis], bound)


@dataclass
class _SurfaceProjector3D:
    """Projects a 3D point outside the convex hull onto one ASV/choke boundary surface
    (minimum rate, maximum rate, minimum discharge pressure, or maximum suction pressure),
    by first clamping the two other coordinates to their own 1D boundaries and then reading
    the projected axis value off the boundary surface, before evaluating energy usage there.
    """

    axis: int
    variable_axes: tuple[int, int]
    kind: Literal["lower", "upper"]
    first_boundary: _Boundary1D
    second_boundary: _Boundary1D
    surface_function: LinearSurfaceInterpolator
    energy_function: LinearNDInterpolator

    @classmethod
    def build(
        cls,
        convex_hull: ConvexHull,
        points: FloatArray,
        values: FloatArray,
        axis: int,
        source: Literal["lower", "upper", "upper_monotonic"],
        boundaries: tuple[tuple[int, Literal["lower", "upper"]], tuple[int, Literal["lower", "upper"]]],
        fill_value: float,
    ) -> _SurfaceProjector3D:
        half_hull = _select_half_hull(convex_hull, axis=axis, source=source)
        variable_axes = cast(tuple[int, int], tuple(index for index in range(points.shape[1]) if index != axis))
        reduced_points = half_hull.points[:, variable_axes]
        reduced_hull = ConvexHull(reduced_points)
        reduced_axes = {original_axis: reduced_axis for reduced_axis, original_axis in enumerate(variable_axes)}
        boundary_functions: list[_Boundary1D] = []
        for output_axis, kind in boundaries:
            input_axis = next(original_axis for original_axis in variable_axes if original_axis != output_axis)
            edge = _select_half_hull(reduced_hull, axis=reduced_axes[output_axis], source=kind).points
            boundary_functions.append(
                _Boundary1D(
                    input_axis=input_axis,
                    output_axis=output_axis,
                    kind=kind,
                    function=_make_interp1d(
                        edge,
                        input_axis=1 - reduced_axes[output_axis],
                        output_axis=reduced_axes[output_axis],
                        sort_axis=reduced_axes[output_axis] if source == "upper_monotonic" else None,
                    ),
                )
            )
        surface_indices = np.asarray(half_hull.original_indices, dtype=np.int64)
        return cls(
            axis=axis,
            variable_axes=variable_axes,
            kind="lower" if source == "lower" else "upper",
            first_boundary=boundary_functions[0],
            second_boundary=boundary_functions[1],
            surface_function=LinearSurfaceInterpolator(
                half_convex_hull=half_hull.reorder_axes(axis=axis, variable_axes=list(variable_axes)),
                fill_value=fill_value,
            ),
            energy_function=LinearNDInterpolator(
                points[surface_indices][:, variable_axes],
                values[surface_indices],
                fill_value=np.nan,
                rescale=False,
            ),
        )

    def _point(self, coordinates: list[float]) -> list[float]:
        return [coordinates[self.variable_axes[0]], coordinates[self.variable_axes[1]]]

    def project_domain(self, coordinates: list[float]) -> list[float]:
        projected = list(coordinates)
        self.first_boundary.apply(projected)
        self.second_boundary.apply(projected)
        return projected

    def bound(self, coordinates: list[float]) -> tuple[list[float], float]:
        projected = self.project_domain(coordinates)
        return projected, _evaluate_surface(self.surface_function, self._point(projected))

    def project_point(self, coordinates: list[float], epsilon: float) -> list[float]:
        projected, bound = self.bound(coordinates)
        if self.kind == "lower":
            projected[self.axis] = _scalar_fmax(projected[self.axis], bound + epsilon)
        else:
            projected[self.axis] = _scalar_fmin(projected[self.axis], bound - epsilon)
        return projected

    def evaluate_energy(self, coordinates: list[float]) -> float:
        return _evaluate_nd_interpolator(self.energy_function, self._point(coordinates))


def _fill_values(sorted_points: FloatArray, output_axis: int) -> tuple[float, float]:
    """Extrapolation fill values: the boundary's own output value at each end of its
    sampled input range, used below/above that range instead of NaN."""
    return float(sorted_points[0, output_axis]), float(sorted_points[-1, output_axis])


def _make_interp1d(
    points: FloatArray,
    input_axis: int,
    output_axis: int,
    fill_value: tuple[float, float] | None = None,
    sort_axis: int | None = None,
) -> interp1d:
    """Build a 1D boundary function (output_axis as a function of input_axis) from the
    edge points of a half convex hull.

    sort_axis picks which column determines the fill-value order (min/max at either end of x's
    range). It defaults to input_axis, so x itself ends up sorted and scipy can trust our
    ordering (assume_sorted=True). The only caller that passes a differing sort_axis is
    _SurfaceProjector3D.build's 3D max-rate boundary, which (matching legacy) must sort by
    the output column instead; there x is not guaranteed sorted, so scipy must sort
    internally (assume_sorted=False). 2D boundaries built via _build_boundary always sort by
    input_axis, even for their own "upper monotonic" source - do not change that to match
    the 3D case.
    """
    sorted_points = sort_ndarray_by_column(points, input_axis if sort_axis is None else sort_axis)
    return interp1d(
        x=sorted_points[:, input_axis],
        y=sorted_points[:, output_axis],
        fill_value=_fill_values(sorted_points, output_axis) if fill_value is None else fill_value,
        bounds_error=False,
        assume_sorted=sort_axis is None,
    )


def _select_half_hull(
    convex_hull: ConvexHull,
    axis: int,
    source: Literal["lower", "upper", "upper_monotonic"],
    case_2d: str = "rate_ps",
) -> HalfConvexHull:
    """Pick the lower, upper, or upper-monotonic half of a convex hull split along axis."""
    lower, upper, upper_monotonic = get_lower_upper_qhull(convex_hull, axis=axis, case_2d=case_2d)
    if source == "lower":
        return lower
    if source == "upper":
        return upper
    if upper_monotonic is None:
        raise IllegalStateException("Upper monotonic convex hull is not available.")
    return upper_monotonic


def _build_boundary(
    convex_hull: ConvexHull,
    input_axis: int,
    output_axis: int,
    kind: Literal["lower", "upper"],
    case_2d: str = "rate_ps",
    source: Literal["lower", "upper", "upper_monotonic"] | None = None,
    fill_value: tuple[float, float] | None = None,
) -> _Boundary1D:
    """Build a _Boundary1D from the requested half hull's edge (used by SampledCompressor2D)."""
    edge = _select_half_hull(convex_hull, axis=output_axis, source=source or kind, case_2d=case_2d).points
    return _Boundary1D(
        input_axis=input_axis,
        output_axis=output_axis,
        kind=kind,
        function=_make_interp1d(edge, input_axis=input_axis, output_axis=output_axis, fill_value=fill_value),
    )


# --- End ASV/choke boundary and surface projection helpers ------------------------


class SampledCompressor1D:
    """Interpolates energy usage over a single active variable (rate, ps, or pd - the
    other two are missing or degenerate), via monotone piecewise-linear interpolation.
    Outside the sampled range, one side is extrapolated flat (held at the boundary
    sample's value) and the other is NaN: for rate/pd, flat below and NaN above; for
    ps, NaN below and flat above."""

    def __init__(self, variable: VariableName, points: FloatArray, values: FloatArray) -> None:
        order = np.argsort(points)
        sorted_points = points[order]
        sorted_values = values[order]
        if np.unique(sorted_points).size != sorted_points.size:
            duplicates = sorted_points[np.flatnonzero(np.diff(sorted_points) == 0)]
            duplicate_text = ", ".join(str(value) for value in duplicates)
            raise IllegalStateException(
                f"1D compressor sampled data require unique variable input values. I got non-unique {variable} values {duplicate_text}"
            )
        fill_value = (np.nan, float(sorted_values[-1])) if variable == PS_NAME else (float(sorted_values[0]), np.nan)
        self._variable = variable
        self._max_rate = float(sorted_points[-1]) if variable == RATE_NAME else None
        self.support_max_rate = variable == RATE_NAME
        self._interpolator = interp1d(
            x=sorted_points,
            y=sorted_values,
            fill_value=fill_value,
            bounds_error=False,
            assume_sorted=True,
        )

    def evaluate(
        self,
        rate: float | None = None,
        suction_pressure: float | None = None,
        discharge_pressure: float | None = None,
    ) -> float:
        variable = {
            RATE_NAME: rate,
            PS_NAME: suction_pressure,
            PD_NAME: discharge_pressure,
        }[self._variable]
        if variable is None:
            raise IllegalStateException(f"Missing evaluation data for {self._variable}")
        return _evaluate_interp1d(self._interpolator, variable)

    def get_max_rate(self) -> float | None:
        return self._max_rate


class SampledCompressor2D:
    """Interpolates energy usage over two active variables - (rate, ps), (rate, pd), or
    (ps, pd) - via Delaunay-based linear interpolation inside the sample points' convex
    hull, and ASV/choke boundary projection (see the section above) outside it."""

    def __init__(self, variables: tuple[VariableName, VariableName], points: FloatArray, values: FloatArray) -> None:
        self.variables = variables
        self.support_max_rate = RATE_NAME in variables
        self._interpolator = LinearNDInterpolator(points, values, fill_value=np.nan, rescale=True)
        convex_hull = ConvexHull(points)
        if variables == (RATE_NAME, PD_NAME):
            self._minimum_rate = _build_boundary(
                convex_hull, input_axis=1, output_axis=0, kind="lower", case_2d="rate_pd"
            )
            self._minimum_pd = _build_boundary(
                convex_hull, input_axis=0, output_axis=1, kind="lower", case_2d="rate_pd"
            )
            upper_points = _select_half_hull(convex_hull, axis=0, source="upper_monotonic", case_2d="rate_pd").points
            upper_sorted = sort_ndarray_by_column(upper_points, 1)
            self._maximum_rate = _build_boundary(
                convex_hull,
                input_axis=1,
                output_axis=0,
                kind="upper",
                case_2d="rate_pd",
                source="upper_monotonic",
                fill_value=(float(upper_sorted[0, 0]), 0.0),
            )
        elif variables == (RATE_NAME, PS_NAME):
            self._minimum_rate = _build_boundary(
                convex_hull, input_axis=1, output_axis=0, kind="lower", case_2d="rate_ps"
            )
            self._maximum_ps = _build_boundary(
                convex_hull, input_axis=0, output_axis=1, kind="upper", case_2d="rate_ps"
            )
            upper_points = _select_half_hull(convex_hull, axis=0, source="upper_monotonic", case_2d="rate_ps").points
            upper_sorted = sort_ndarray_by_column(upper_points, 1)
            self._maximum_rate = _build_boundary(
                convex_hull,
                input_axis=1,
                output_axis=0,
                kind="upper",
                case_2d="rate_ps",
                source="upper_monotonic",
                fill_value=(0.0, float(upper_sorted[-1, 0])),
            )
        elif variables == (PS_NAME, PD_NAME):
            self._minimum_pd = _build_boundary(convex_hull, input_axis=0, output_axis=1, kind="lower")
            self._maximum_ps = _build_boundary(convex_hull, input_axis=1, output_axis=0, kind="upper")
        else:
            raise IllegalStateException(f"Unsupported 2D variables: {variables}")

    def _project(
        self,
        rate: float | None = None,
        suction_pressure: float | None = None,
        discharge_pressure: float | None = None,
    ) -> list[float]:
        if self.variables == (RATE_NAME, PD_NAME):
            if rate is None or discharge_pressure is None:
                raise IllegalStateException("Missing rate or discharge pressure")
            projected_rate = _scalar_fmax(rate, _evaluate_interp1d(self._minimum_rate.function, discharge_pressure))
            projected_pd = _scalar_fmax(
                discharge_pressure,
                _evaluate_interp1d(self._minimum_pd.function, projected_rate),
            )
            return [projected_rate, projected_pd]
        if self.variables == (RATE_NAME, PS_NAME):
            if rate is None or suction_pressure is None:
                raise IllegalStateException("Missing rate or suction pressure")
            projected_rate = _scalar_fmax(rate, _evaluate_interp1d(self._minimum_rate.function, suction_pressure))
            projected_ps = _scalar_fmin(
                suction_pressure,
                _evaluate_interp1d(self._maximum_ps.function, projected_rate),
            )
            return [projected_rate, projected_ps]
        if suction_pressure is None or discharge_pressure is None:
            raise IllegalStateException("Missing suction or discharge pressure")
        projected_pd = _scalar_fmax(
            discharge_pressure,
            _evaluate_interp1d(self._minimum_pd.function, suction_pressure),
        )
        projected_ps = _scalar_fmin(
            suction_pressure,
            _evaluate_interp1d(self._maximum_ps.function, projected_pd),
        )
        return [projected_ps, projected_pd]

    def evaluate(
        self,
        rate: float | None = None,
        suction_pressure: float | None = None,
        discharge_pressure: float | None = None,
    ) -> float:
        return _evaluate_nd_interpolator(
            self._interpolator,
            self._project(rate=rate, suction_pressure=suction_pressure, discharge_pressure=discharge_pressure),
        )

    def get_max_rate(
        self,
        suction_pressure: float | None = None,
        discharge_pressure: float | None = None,
    ) -> float:
        if self.variables == (RATE_NAME, PD_NAME):
            if discharge_pressure is None:
                raise IllegalStateException("Missing discharge pressure")
            return _evaluate_interp1d(self._maximum_rate.function, discharge_pressure)
        if self.variables == (RATE_NAME, PS_NAME):
            if suction_pressure is None:
                raise IllegalStateException("Missing suction pressure")
            return _evaluate_interp1d(self._maximum_rate.function, suction_pressure)
        raise IllegalStateException("Maximum rate is not supported for this 2D model")


class SampledCompressor3D:
    """Interpolates energy usage over all three variables (rate, ps, pd) via
    Delaunay-based linear interpolation inside the sample points' convex hull, and
    ASV/choke boundary projection (see the section above) outside it. Optionally
    rescales the rate axis before triangulating, so its magnitude is comparable to
    ps/pd (otherwise Delaunay triangulation is numerically unstable when rate spans
    orders of magnitude more than ps/pd)."""

    support_max_rate = True

    def __init__(self, points: FloatArray, values: FloatArray, rescale_rate: bool = True) -> None:
        self._scale_factor_rate = float(
            round(2 * points[:, 0].mean() / (points[:, 1].mean() + points[:, 2].mean())) if rescale_rate else 1.0
        )
        self._do_rescale = rescale_rate
        scaled_points = points.copy()
        if self._do_rescale:
            scaled_points[:, 0] /= self._scale_factor_rate
        convex_hull = ConvexHull(scaled_points)
        self._rate_limits = (float(convex_hull.min_bound[0]), float(convex_hull.max_bound[0]))
        self._interpolator = LinearNDInterpolator(Delaunay(scaled_points), values, fill_value=np.nan, rescale=False)
        self._minimum_rate = _SurfaceProjector3D.build(
            convex_hull,
            scaled_points,
            values,
            axis=0,
            source="lower",
            boundaries=((2, "lower"), (1, "upper")),
            fill_value=0.0,
        )
        self._maximum_rate = _SurfaceProjector3D.build(
            convex_hull,
            scaled_points,
            values,
            axis=0,
            source="upper_monotonic",
            boundaries=((2, "lower"), (1, "upper")),
            fill_value=0.0,
        )
        self._minimum_pd = _SurfaceProjector3D.build(
            convex_hull,
            scaled_points,
            values,
            axis=2,
            source="lower",
            boundaries=((0, "lower"), (1, "upper")),
            fill_value=0.0,
        )
        self._maximum_ps = _SurfaceProjector3D.build(
            convex_hull,
            scaled_points,
            values,
            axis=1,
            source="upper",
            boundaries=((0, "lower"), (2, "lower")),
            fill_value=np.inf,
        )

    def _scale_rate(self, rate: float) -> float:
        return rate / self._scale_factor_rate if self._do_rescale else rate

    @staticmethod
    def _coordinates(rate: float, suction_pressure: float, discharge_pressure: float) -> list[float]:
        return [rate, suction_pressure, discharge_pressure]

    def project_variables(
        self,
        rate: float,
        suction_pressure: float,
        discharge_pressure: float,
    ) -> tuple[float, float, float]:
        projected = self._minimum_rate.project_point(
            self._coordinates(rate, suction_pressure, discharge_pressure), EPSILON
        )
        projected = self._minimum_pd.project_point(projected, EPSILON)
        projected = self._maximum_ps.project_point(projected, EPSILON)
        return projected[0], projected[1], projected[2]

    def get_max_rate(self, suction_pressure: float, discharge_pressure: float) -> float:
        _, maximum_rate = self._maximum_rate.bound(self._coordinates(0.0, suction_pressure, discharge_pressure))
        return maximum_rate * self._scale_factor_rate if self._do_rescale else maximum_rate

    def _evaluate_outside_rate(self, coordinates: list[float]) -> float:
        # Compute the minimum-rate branch first, then let a matching maximum-rate branch
        # overwrite it - the two conditions aren't mutually exclusive (e.g. at a hull
        # corner, or when querying exactly at get_max_rate()'s own output), and legacy's
        # evaluation order means maximum-rate wins when both match.
        tolerance = (self._rate_limits[1] - self._rate_limits[0]) * EPSILON_MAX_RATE
        result = math.nan
        projected, minimum_rates = self._minimum_rate.bound(coordinates)
        if coordinates[0] <= minimum_rates + tolerance:
            result = self._minimum_rate.evaluate_energy(projected)
        projected, maximum_rates = self._maximum_rate.bound(coordinates)
        if abs(coordinates[0] - maximum_rates) < tolerance:
            result = self._maximum_rate.evaluate_energy(projected)
        return result

    def _evaluate_outside_pd(self, coordinates: list[float]) -> float:
        projected, minimum_pd = self._minimum_pd.bound(coordinates)
        if coordinates[2] <= minimum_pd:
            return self._minimum_pd.evaluate_energy(projected)
        return math.nan

    def _evaluate_outside_ps(self, coordinates: list[float]) -> float:
        projected, maximum_ps = self._maximum_ps.bound(coordinates)
        if coordinates[1] >= maximum_ps:
            return self._maximum_ps.evaluate_energy(projected)
        return math.nan

    def evaluate(
        self,
        rate: float,
        suction_pressure: float,
        discharge_pressure: float,
    ) -> float:
        coordinates = self._coordinates(self._scale_rate(rate), suction_pressure, discharge_pressure)
        result = _evaluate_nd_interpolator(self._interpolator, coordinates)
        if math.isnan(result):
            result = self._evaluate_outside_rate(coordinates)
        if math.isnan(result):
            result = self._evaluate_outside_pd(coordinates)
        if math.isnan(result):
            result = self._evaluate_outside_ps(coordinates)
        return result


class SampledCompressor:
    """Dispatches evaluate()/get_max_standard_rate() to a 1D, 2D, or 3D interpolator,
    chosen automatically from which of rate/suction_pressure/discharge_pressure are
    both provided and non-degenerate (i.e. actually vary across the sample table).
    Rate values at or below zero are treated as "off" (energy_usage=0) without calling
    the underlying model; if rate, ps, or pd is provided but degenerate (only one
    sampled value), its single value acts as a hard limit for queries in the direction
    the model has no data for (query rate above it, ps below it, or pd above it),
    which are set to NaN instead of being evaluated. Optionally also interpolates
    power from energy usage, if power_interpolation_values is provided."""

    def __init__(
        self,
        energy_usage_values: list[float],
        rate_values: list[float] | None = None,
        suction_pressure_values: list[float] | None = None,
        discharge_pressure_values: list[float] | None = None,
        power_interpolation_values: list[float] | None = None,
    ) -> None:
        self.energy_usage_values = energy_usage_values
        self.rate_values = rate_values
        self.suction_pressure_values = suction_pressure_values
        self.discharge_pressure_values = discharge_pressure_values
        self.power_interpolation_values = power_interpolation_values
        self._validate()
        self._power_function = self._build_power_function(power_interpolation_values)
        self._provided_variables = {
            name: _as_float_array(values)
            for name, values in (
                (RATE_NAME, rate_values),
                (PS_NAME, suction_pressure_values),
                (PD_NAME, discharge_pressure_values),
            )
            if values is not None
        }
        self.required_variables = list(self._provided_variables)
        self.active_variables = tuple(
            cast(VariableName, name) for name, values in self._provided_variables.items() if np.unique(values).size != 1
        )
        if not self.active_variables:
            raise IllegalStateException("At least one variable must be non-degenerate.")
        self._degenerated_rate = (
            float(self._provided_variables[RATE_NAME][0])
            if RATE_NAME in self.required_variables and RATE_NAME not in self.active_variables
            else np.inf
        )
        self._degenerated_ps = (
            float(self._provided_variables[PS_NAME][0])
            if PS_NAME in self.required_variables and PS_NAME not in self.active_variables
            else -np.inf
        )
        self._degenerated_pd = (
            float(self._provided_variables[PD_NAME][0])
            if PD_NAME in self.required_variables and PD_NAME not in self.active_variables
            else np.inf
        )
        self.support_max_rate = RATE_NAME in self.required_variables
        self._model = self._build_model(_as_float_array(energy_usage_values))

    def _validate(self) -> None:
        if not self.rate_values and not self.suction_pressure_values and not self.discharge_pressure_values:
            raise ProcessMissingVariableValidationException(
                message="Need at least one variable for CompressorTrainSampled (rate, suction_pressure or discharge_pressure)"
            )
        count = len(self.energy_usage_values)
        for name in (
            "rate_values",
            "suction_pressure_values",
            "discharge_pressure_values",
            "power_interpolation_values",
        ):
            values = getattr(self, name)
            if values is not None and len(values) != count:
                raise ProcessEqualLengthValidationException(
                    message=f"{name} has wrong number of points. Should have {count} (equal to number of energy usage value points)"
                )
        for name in (
            "energy_usage_values",
            "rate_values",
            "suction_pressure_values",
            "discharge_pressure_values",
            "power_interpolation_values",
        ):
            values = getattr(self, name)
            if values is None:
                continue
            for row_index, value in enumerate(values):
                try:
                    float(value)
                except ValueError as error:
                    raise InvalidColumnException(
                        header=name,
                        message=f"Got non-numeric value '{value}'.",
                        row_index=row_index,
                    ) from error
            if any(value < 0 for value in values):
                raise ProcessNegativeValuesValidationException(
                    message=f"All values in {name} must be greater than or equal to 0"
                )

    def _build_power_function(self, power_values: list[float] | None) -> interp1d | None:
        if power_values is None:
            self._fuel_power_samples = None
            return None
        fuel_values = _as_float_array(self.energy_usage_values)
        power_values_array = _as_float_array(power_values)
        sort_order = np.argsort(fuel_values, kind="stable")
        self._fuel_power_samples = (fuel_values[sort_order], power_values_array[sort_order])
        return interp1d(fuel_values, power_values_array, fill_value=(0, np.nan), bounds_error=False)

    def get_fuel_power_samples(self) -> tuple[FloatArray, FloatArray] | None:
        """Sorted (fuel, power) samples this model's power function uses."""
        return self._fuel_power_samples

    def _build_model(
        self,
        energy_usage_values: FloatArray,
    ) -> SampledCompressor1D | SampledCompressor2D | SampledCompressor3D:
        if len(self.active_variables) == 1:
            variable = cast(VariableName, self.active_variables[0])
            return SampledCompressor1D(variable, self._provided_variables[variable], energy_usage_values)
        if len(self.active_variables) == 2:
            return SampledCompressor2D(
                cast(tuple[VariableName, VariableName], self.active_variables),
                np.column_stack([self._provided_variables[name] for name in self.active_variables]),
                energy_usage_values,
            )
        return SampledCompressor3D(
            np.column_stack(
                [
                    self._provided_variables[RATE_NAME],
                    self._provided_variables[PS_NAME],
                    self._provided_variables[PD_NAME],
                ]
            ),
            energy_usage_values,
        )

    def evaluate(
        self,
        rate: float | None = None,
        suction_pressure: float | None = None,
        discharge_pressure: float | None = None,
    ) -> SampledCompressorResult:
        rate_value = rate
        suction_pressure_value = suction_pressure
        discharge_pressure_value = discharge_pressure
        if rate_value is None and suction_pressure_value is None and discharge_pressure_value is None:
            raise IllegalStateException("Need at least one evaluation variable")
        if rate_value is not None and rate_value > 0:
            rate_value -= EPSILON
        energy_usage = math.nan
        if rate_value is not None and rate_value <= 0:
            energy_usage = 0.0
        rate_ok = rate_value is None or 0 < rate_value <= self._degenerated_rate
        ps_ok = suction_pressure_value is None or suction_pressure_value >= self._degenerated_ps
        pd_ok = discharge_pressure_value is None or discharge_pressure_value <= self._degenerated_pd
        if math.isnan(energy_usage) and rate_ok and ps_ok and pd_ok:
            if isinstance(self._model, SampledCompressor3D):
                if rate_value is None or suction_pressure_value is None or discharge_pressure_value is None:
                    raise IllegalStateException(
                        "3D sampled compressor evaluation needs rate, suction pressure and discharge pressure"
                    )
                energy_usage = self._model.evaluate(
                    rate=rate_value,
                    suction_pressure=suction_pressure_value,
                    discharge_pressure=discharge_pressure_value,
                )
            else:
                energy_usage = self._model.evaluate(
                    rate=rate_value,
                    suction_pressure=suction_pressure_value,
                    discharge_pressure=discharge_pressure_value,
                )
        power = None if self._power_function is None else _evaluate_interp1d(self._power_function, energy_usage)
        return SampledCompressorResult(energy_usage=energy_usage, power=power)

    def get_max_standard_rate(
        self,
        suction_pressure: float | None = None,
        discharge_pressure: float | None = None,
    ) -> float:
        if not self.support_max_rate:
            return math.nan
        if not self._model.support_max_rate:
            return self._degenerated_rate
        if isinstance(self._model, SampledCompressor1D):
            max_rate = self._model.get_max_rate()
            if max_rate is None:
                raise IllegalStateException("Maximum rate is not available for this 1D model")
            return max_rate
        if isinstance(self._model, SampledCompressor2D):
            return self._model.get_max_rate(
                suction_pressure=suction_pressure,
                discharge_pressure=discharge_pressure,
            )
        if suction_pressure is None or discharge_pressure is None:
            raise IllegalStateException("Need suction and discharge pressures to compute maximum rate")
        return self._model.get_max_rate(suction_pressure=suction_pressure, discharge_pressure=discharge_pressure)


__all__ = [
    "EPSILON",
    "PD_NAME",
    "PS_NAME",
    "RATE_NAME",
    "SampledCompressor",
    "SampledCompressor1D",
    "SampledCompressor2D",
    "SampledCompressor3D",
    "SampledCompressorResult",
]
