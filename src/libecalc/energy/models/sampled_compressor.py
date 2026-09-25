"""Dependency-free reimplementation of the legacy sampled compressor model: interpolates
energy usage (and, optionally, power) from a table of sampled points over rate, suction
pressure (ps), and/or discharge pressure (pd), dropping any missing or degenerate
(constant) input from the model.

Build a model via SampledCompressorFactory.create() (in the sibling
sampled_compressor_factory module), which validates the raw sample table, derives
SampledCompressorData (in the sibling sampled_compressor_data module), and picks the
matching 1D, 2D, or 3D implementation below for whichever of rate/ps/pd are provided
and non-degenerate. SampledCompressorBase implements the evaluate()/
get_max_standard_rate() template methods every implementation shares. The 2D/3D
interpolators extrapolate outside the sample points' convex hull via
libecalc.energy.models.convex_hull and the "ASV/choke boundary and surface projection
helpers" section below.

Reimplements, without any dependency on libecalc.domain, the model classes from
libecalc.domain.process.compressor.core.sampled: CompressorModelSampled (as
SampledCompressor/SampledCompressorFactory), CompressorModelSampled1D (as
_RateCompressor1D/_SuctionPressureCompressor1D/_DischargePressureCompressor1D),
CompressorModelSampled2DRatePs/RatePd/PsPd (as
_RatePsCompressor2D/_RatePdCompressor2D/_PsPdCompressor2D), and CompressorModelSampled3D
(as _SampledCompressor3D).
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import ClassVar, Literal, cast

import numpy as np
from scipy.interpolate import LinearNDInterpolator, interp1d
from scipy.spatial import ConvexHull, Delaunay

from libecalc.common.errors.exceptions import IllegalStateException
from libecalc.energy.models.convex_hull import (
    FloatArray,
    HalfConvexHull,
    LinearSurfaceInterpolator,
    get_lower_upper_qhull,
    sort_ndarray_by_column,
)
from libecalc.energy.models.fuel_power_curve import FuelPowerCurve
from libecalc.energy.models.sampled_compressor_data import (
    PD_NAME,
    PS_NAME,
    RATE_NAME,
    SampledCompressorData,
    VariableName,
    _as_float_array,
)

EPSILON = 1e-15
EPSILON_MAX_RATE = 1e-4


@dataclass(frozen=True)
class SampledCompressorResult:
    """The result of one SampledCompressor.evaluate() query."""

    energy_usage: float
    power: float | None = None


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
# Used by the 2D/3D implementations below to extrapolate outside the convex hull of
# the sampled data, reimplementing the boundary/projection logic from legacy
# compressor_model_sampled_2d.py and compressor_model_sampled_3d.py.


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
    """Projects a 3D point outside the convex hull onto one ASV/choke boundary surface,
    by clamping the two other coordinates to their own 1D boundaries and reading the
    projected axis value off the boundary surface, before evaluating energy usage there."""

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
    edge points of a half convex hull. sort_axis defaults to input_axis, so x is sorted
    and scipy trusts our ordering; the one exception is _SurfaceProjector3D's 3D max-rate
    boundary, which must sort by the output column instead, so scipy sorts internally."""
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
    """Build a _Boundary1D from the requested half hull's edge."""
    edge = _select_half_hull(convex_hull, axis=output_axis, source=source or kind, case_2d=case_2d).points
    return _Boundary1D(
        input_axis=input_axis,
        output_axis=output_axis,
        kind=kind,
        function=_make_interp1d(edge, input_axis=input_axis, output_axis=output_axis, fill_value=fill_value),
    )


# --- End ASV/choke boundary and surface projection helpers ------------------------


class SampledCompressor(ABC):
    """Public interface for every sampled-compressor implementation below. Construct via
    SampledCompressorFactory.create()."""

    support_max_rate: bool = False

    @abstractmethod
    def evaluate(
        self,
        rate: float | None = None,
        suction_pressure: float | None = None,
        discharge_pressure: float | None = None,
    ) -> SampledCompressorResult: ...

    @abstractmethod
    def get_max_standard_rate(
        self,
        suction_pressure: float | None = None,
        discharge_pressure: float | None = None,
    ) -> float: ...

    @abstractmethod
    def get_fuel_power_curve(self) -> FuelPowerCurve | None:
        """This model's fuel/power relation, if it has one."""


class SampledCompressorBase(SampledCompressor):
    """Shared base for every concrete SampledCompressor implementation: takes an
    already-validated SampledCompressorData and implements the
    evaluate()/get_max_standard_rate() template methods every implementation shares.
    Each subclass declares its required active-variable combination via
    _active_variables (checked below, so a class built from mismatched data is
    rejected immediately rather than silently misreading the wrong column), and only
    implements _evaluate_active() (and _get_max_rate_active(), if it supports rate).

    Rate values at or below zero are treated as "off" (energy_usage=0); if rate, ps,
    or pd is provided but degenerate (one sampled value), that value is a hard limit
    for queries beyond it, which return NaN instead of being evaluated."""

    _active_variables: ClassVar[tuple[VariableName, ...]] = ()

    def __init__(self, table: SampledCompressorData) -> None:
        if table.active_variables != self._active_variables:
            raise IllegalStateException(
                f"{type(self).__name__} requires active variables to be "
                f"{self._active_variables}, got {table.active_variables}"
            )
        self._table = table

    @property
    def energy_usage_values(self) -> list[float]:
        return self._table.energy_usage_values

    @property
    def required_variables(self) -> list[VariableName]:
        return self._table.required_variables

    @property
    def active_variables(self) -> tuple[VariableName, ...]:
        return self._table.active_variables

    @property
    def _provided_variables(self) -> dict[VariableName, FloatArray]:
        return self._table.provided_variables

    @property
    def _degenerated_rate(self) -> float:
        return self._table.degenerated_rate

    @property
    def _degenerated_ps(self) -> float:
        return self._table.degenerated_ps

    @property
    def _degenerated_pd(self) -> float:
        return self._table.degenerated_pd

    def get_fuel_power_curve(self) -> FuelPowerCurve | None:
        return self._table.fuel_power_curve

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
            energy_usage = self._evaluate_active(rate_value, suction_pressure_value, discharge_pressure_value)
        curve = self.get_fuel_power_curve()
        power = None if curve is None else curve.power_for_fuel(energy_usage)
        return SampledCompressorResult(energy_usage=energy_usage, power=power)

    @abstractmethod
    def _evaluate_active(
        self,
        rate: float | None,
        suction_pressure: float | None,
        discharge_pressure: float | None,
    ) -> float:
        """Evaluate energy usage for whichever variable(s) this implementation is
        actually built over - self._degenerated_*/rate<=0 handling already applied by
        evaluate() above."""

    def get_max_standard_rate(
        self,
        suction_pressure: float | None = None,
        discharge_pressure: float | None = None,
    ) -> float:
        if RATE_NAME not in self.required_variables:
            return math.nan
        if not self.support_max_rate:
            return self._degenerated_rate
        return self._get_max_rate_active(suction_pressure=suction_pressure, discharge_pressure=discharge_pressure)

    def _get_max_rate_active(
        self,
        suction_pressure: float | None = None,
        discharge_pressure: float | None = None,
    ) -> float:
        raise IllegalStateException("Maximum rate is not supported for this model")

    def _build_1d_interpolator(
        self, variable: VariableName, flat_side: Literal["low", "high"]
    ) -> tuple[interp1d, FloatArray]:
        """Builds a monotone piecewise-linear interpolator over a single active
        variable, sorted by that variable's sampled values (also returned, sorted, so
        callers needing e.g. the maximum sampled rate don't have to re-sort). Outside
        the sampled range, flat_side is extrapolated flat (held at that boundary
        sample's value) and the other side is NaN. Raises if any sampled value
        repeats - it is undefined which energy usage a repeated sample would
        correspond to."""
        points = self._provided_variables[variable]
        values = _as_float_array(self.energy_usage_values)
        order = np.argsort(points)
        sorted_points = points[order]
        sorted_values = values[order]
        if np.unique(sorted_points).size != sorted_points.size:
            duplicates = sorted_points[np.flatnonzero(np.diff(sorted_points) == 0)]
            duplicate_text = ", ".join(str(value) for value in duplicates)
            raise IllegalStateException(
                f"1D compressor sampled data require unique variable input values. I got non-unique {variable} values {duplicate_text}"
            )
        fill_value = (float(sorted_values[0]), np.nan) if flat_side == "low" else (np.nan, float(sorted_values[-1]))
        interpolator = interp1d(
            x=sorted_points,
            y=sorted_values,
            fill_value=fill_value,
            bounds_error=False,
            assume_sorted=True,
        )
        return interpolator, sorted_points

    def _build_nd_interpolator_and_hull(self) -> tuple[LinearNDInterpolator, ConvexHull]:
        """Builds the Delaunay-based linear interpolator and its convex hull over this
        model's active variables, for 2D leaf classes' ASV/choke boundary
        projection."""
        points = np.column_stack([self._provided_variables[name] for name in self.active_variables])
        values = _as_float_array(self.energy_usage_values)
        interpolator = LinearNDInterpolator(points, values, fill_value=np.nan, rescale=True)
        return interpolator, ConvexHull(points)


class _RateCompressor1D(SampledCompressorBase):
    """Interpolates energy usage over rate alone (suction/discharge pressure are
    missing or degenerate), via monotone piecewise-linear interpolation: extrapolated
    flat (held at the minimum sampled rate's value) below the sampled range, and NaN
    above it."""

    _active_variables: ClassVar[tuple[VariableName, ...]] = (RATE_NAME,)
    support_max_rate = True

    def __init__(self, table: SampledCompressorData) -> None:
        super().__init__(table)
        self._interpolator, sorted_points = self._build_1d_interpolator(RATE_NAME, flat_side="low")
        self._max_rate = float(sorted_points[-1])

    def _evaluate_active(
        self,
        rate: float | None,
        suction_pressure: float | None,
        discharge_pressure: float | None,
    ) -> float:
        if rate is None:
            raise IllegalStateException("Missing evaluation data for RATE")
        return _evaluate_interp1d(self._interpolator, rate)

    def _get_max_rate_active(
        self,
        suction_pressure: float | None = None,
        discharge_pressure: float | None = None,
    ) -> float:
        return self._max_rate


class _SuctionPressureCompressor1D(SampledCompressorBase):
    """Interpolates energy usage over suction pressure alone (rate/discharge pressure
    are missing or degenerate), via monotone piecewise-linear interpolation:
    extrapolated NaN below the sampled range, and flat (held at the maximum sampled
    suction pressure's value) above it. Has no rate axis, so support_max_rate stays
    False and _get_max_rate_active() is never reached."""

    _active_variables: ClassVar[tuple[VariableName, ...]] = (PS_NAME,)

    def __init__(self, table: SampledCompressorData) -> None:
        super().__init__(table)
        self._interpolator, _ = self._build_1d_interpolator(PS_NAME, flat_side="high")

    def _evaluate_active(
        self,
        rate: float | None,
        suction_pressure: float | None,
        discharge_pressure: float | None,
    ) -> float:
        if suction_pressure is None:
            raise IllegalStateException("Missing evaluation data for SUCTION_PRESSURE")
        return _evaluate_interp1d(self._interpolator, suction_pressure)


class _DischargePressureCompressor1D(SampledCompressorBase):
    """Interpolates energy usage over discharge pressure alone (rate/suction pressure
    are missing or degenerate), via monotone piecewise-linear interpolation:
    extrapolated flat (held at the minimum sampled discharge pressure's value) below
    the sampled range, and NaN above it. Has no rate axis, so support_max_rate stays
    False and _get_max_rate_active() is never reached."""

    _active_variables: ClassVar[tuple[VariableName, ...]] = (PD_NAME,)

    def __init__(self, table: SampledCompressorData) -> None:
        super().__init__(table)
        self._interpolator, _ = self._build_1d_interpolator(PD_NAME, flat_side="low")

    def _evaluate_active(
        self,
        rate: float | None,
        suction_pressure: float | None,
        discharge_pressure: float | None,
    ) -> float:
        if discharge_pressure is None:
            raise IllegalStateException("Missing evaluation data for DISCHARGE_PRESSURE")
        return _evaluate_interp1d(self._interpolator, discharge_pressure)


class _RatePdCompressor2D(SampledCompressorBase):
    """Interpolates energy usage over (rate, discharge pressure), via Delaunay-based
    linear interpolation inside the sample points' convex hull, and ASV/choke boundary
    projection (see the section above) outside it."""

    _active_variables: ClassVar[tuple[VariableName, ...]] = (RATE_NAME, PD_NAME)
    support_max_rate = True

    def __init__(self, table: SampledCompressorData) -> None:
        super().__init__(table)
        self._interpolator, convex_hull = self._build_nd_interpolator_and_hull()
        self._minimum_rate = _build_boundary(convex_hull, input_axis=1, output_axis=0, kind="lower", case_2d="rate_pd")
        self._minimum_pd = _build_boundary(convex_hull, input_axis=0, output_axis=1, kind="lower", case_2d="rate_pd")
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

    def _evaluate_active(
        self,
        rate: float | None,
        suction_pressure: float | None,
        discharge_pressure: float | None,
    ) -> float:
        if rate is None or discharge_pressure is None:
            raise IllegalStateException("Missing rate or discharge pressure")
        projected_rate = _scalar_fmax(rate, _evaluate_interp1d(self._minimum_rate.function, discharge_pressure))
        projected_pd = _scalar_fmax(discharge_pressure, _evaluate_interp1d(self._minimum_pd.function, projected_rate))
        return _evaluate_nd_interpolator(self._interpolator, [projected_rate, projected_pd])

    def _get_max_rate_active(
        self,
        suction_pressure: float | None = None,
        discharge_pressure: float | None = None,
    ) -> float:
        if discharge_pressure is None:
            raise IllegalStateException("Missing discharge pressure")
        return _evaluate_interp1d(self._maximum_rate.function, discharge_pressure)


class _RatePsCompressor2D(SampledCompressorBase):
    """Interpolates energy usage over (rate, suction pressure), via Delaunay-based
    linear interpolation inside the sample points' convex hull, and ASV/choke boundary
    projection (see the section above) outside it."""

    _active_variables: ClassVar[tuple[VariableName, ...]] = (RATE_NAME, PS_NAME)
    support_max_rate = True

    def __init__(self, table: SampledCompressorData) -> None:
        super().__init__(table)
        self._interpolator, convex_hull = self._build_nd_interpolator_and_hull()
        self._minimum_rate = _build_boundary(convex_hull, input_axis=1, output_axis=0, kind="lower", case_2d="rate_ps")
        self._maximum_ps = _build_boundary(convex_hull, input_axis=0, output_axis=1, kind="upper", case_2d="rate_ps")
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

    def _evaluate_active(
        self,
        rate: float | None,
        suction_pressure: float | None,
        discharge_pressure: float | None,
    ) -> float:
        if rate is None or suction_pressure is None:
            raise IllegalStateException("Missing rate or suction pressure")
        projected_rate = _scalar_fmax(rate, _evaluate_interp1d(self._minimum_rate.function, suction_pressure))
        projected_ps = _scalar_fmin(suction_pressure, _evaluate_interp1d(self._maximum_ps.function, projected_rate))
        return _evaluate_nd_interpolator(self._interpolator, [projected_rate, projected_ps])

    def _get_max_rate_active(
        self,
        suction_pressure: float | None = None,
        discharge_pressure: float | None = None,
    ) -> float:
        if suction_pressure is None:
            raise IllegalStateException("Missing suction pressure")
        return _evaluate_interp1d(self._maximum_rate.function, suction_pressure)


class _PsPdCompressor2D(SampledCompressorBase):
    """Interpolates energy usage over (suction pressure, discharge pressure), via
    Delaunay-based linear interpolation inside the sample points' convex hull, and
    ASV/choke boundary projection (see the section above) outside it. Has no rate
    axis, so support_max_rate stays False and _get_max_rate_active() is never
    reached."""

    _active_variables: ClassVar[tuple[VariableName, ...]] = (PS_NAME, PD_NAME)

    def __init__(self, table: SampledCompressorData) -> None:
        super().__init__(table)
        self._interpolator, convex_hull = self._build_nd_interpolator_and_hull()
        self._minimum_pd = _build_boundary(convex_hull, input_axis=0, output_axis=1, kind="lower")
        self._maximum_ps = _build_boundary(convex_hull, input_axis=1, output_axis=0, kind="upper")

    def _evaluate_active(
        self,
        rate: float | None,
        suction_pressure: float | None,
        discharge_pressure: float | None,
    ) -> float:
        if suction_pressure is None or discharge_pressure is None:
            raise IllegalStateException("Missing suction or discharge pressure")
        projected_pd = _scalar_fmax(discharge_pressure, _evaluate_interp1d(self._minimum_pd.function, suction_pressure))
        projected_ps = _scalar_fmin(suction_pressure, _evaluate_interp1d(self._maximum_ps.function, projected_pd))
        return _evaluate_nd_interpolator(self._interpolator, [projected_ps, projected_pd])


class _SampledCompressor3D(SampledCompressorBase):
    """Interpolates energy usage over all three variables (rate, ps, pd) via
    Delaunay-based linear interpolation inside the sample points' convex hull, and
    ASV/choke boundary projection (see the section above) outside it. Optionally
    rescales the rate axis before triangulating, so its magnitude is comparable to
    ps/pd (otherwise Delaunay triangulation is numerically unstable when rate spans
    orders of magnitude more than ps/pd)."""

    _active_variables: ClassVar[tuple[VariableName, ...]] = (RATE_NAME, PS_NAME, PD_NAME)
    support_max_rate = True

    def __init__(self, table: SampledCompressorData, rescale_rate: bool = True) -> None:
        super().__init__(table)
        points = np.column_stack(
            [
                self._provided_variables[RATE_NAME],
                self._provided_variables[PS_NAME],
                self._provided_variables[PD_NAME],
            ]
        )
        values = _as_float_array(self.energy_usage_values)
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

    def _evaluate_outside_rate(self, coordinates: list[float]) -> float:
        # Evaluate the minimum-rate branch first, then let a matching maximum-rate
        # branch overwrite it - the two aren't mutually exclusive (e.g. at a hull
        # corner), and legacy's evaluation order means maximum-rate wins on a tie.
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

    def _evaluate_active(
        self,
        rate: float | None,
        suction_pressure: float | None,
        discharge_pressure: float | None,
    ) -> float:
        if rate is None or suction_pressure is None or discharge_pressure is None:
            raise IllegalStateException(
                "3D sampled compressor evaluation needs rate, suction pressure and discharge pressure"
            )
        coordinates = self._coordinates(self._scale_rate(rate), suction_pressure, discharge_pressure)
        result = _evaluate_nd_interpolator(self._interpolator, coordinates)
        if math.isnan(result):
            result = self._evaluate_outside_rate(coordinates)
        if math.isnan(result):
            result = self._evaluate_outside_pd(coordinates)
        if math.isnan(result):
            result = self._evaluate_outside_ps(coordinates)
        return result

    def _get_max_rate_active(
        self,
        suction_pressure: float | None = None,
        discharge_pressure: float | None = None,
    ) -> float:
        if suction_pressure is None or discharge_pressure is None:
            raise IllegalStateException("Need suction and discharge pressures to compute maximum rate")
        _, maximum_rate = self._maximum_rate.bound(self._coordinates(0.0, suction_pressure, discharge_pressure))
        return maximum_rate * self._scale_factor_rate if self._do_rescale else maximum_rate


__all__ = [
    "EPSILON",
    "SampledCompressor",
    "SampledCompressorBase",
    "SampledCompressorResult",
]
