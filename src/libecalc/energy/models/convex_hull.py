"""Convex hull geometry for sampled compressor extrapolation.

A sampled compressor is defined by a scattered point cloud of (rate[, ps, pd]) samples
with known energy usage. Queries inside the cloud's convex hull are interpolated
directly; queries outside it (e.g. below the minimum rate, or above the maximum rate)
must be extrapolated by projecting onto the boundary of the sampled envelope instead.

This module builds that boundary: given the convex hull of the sample points, split its
facets into a "lower" half (e.g. minimum rate as a function of the other axes) and an
"upper" half (e.g. maximum rate), each exposed as a single-valued surface that can be
evaluated at arbitrary points via linear interpolation on its own simplices - this is
more robust than re-triangulating with scipy.interpolate.LinearNDInterpolator, whose
triangulation is not guaranteed to preserve the original convex hull's facets.

Reimplements, without any dependency on libecalc.domain, the following symbols from
libecalc.domain.process.compressor.core.sampled.convex_hull_common:
- HalfConvexHull
- sort_ndarray_by_column
- _compute_simplices_in_new_pointset -> _reindex_simplices
- the half-hull construction inside get_lower_upper_qhull -> _build_half_hull
- get_lower_upper_qhull
- Simplex / LinearInterpolatorSimplicesDefined -> LinearSurfaceInterpolator
  (including its _points_inside_simplex / _is_inside)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

import numpy as np
from numpy.typing import NDArray
from scipy.interpolate import LinearNDInterpolator
from scipy.spatial import ConvexHull

FloatArray = NDArray[np.float64]
IntArray = NDArray[np.int64]


@dataclass(frozen=True)
class HalfConvexHull:
    points: FloatArray
    simplices: IntArray
    axis: int
    equations: FloatArray
    original_indices: IntArray

    @property
    def ndim(self) -> int:
        return self.points.shape[1]

    def reorder_axes(self, axis: int, variable_axes: list[int]) -> HalfConvexHull:
        order = [axis, *variable_axes]
        return HalfConvexHull(
            points=self.points[:, order],
            simplices=self.simplices,
            axis=0,
            equations=self.equations[:, order + [-1]],
            original_indices=self.original_indices,
        )


def sort_ndarray_by_column(array: FloatArray, column_index: int) -> FloatArray:
    return np.asarray(array[array[:, column_index].argsort()], dtype=np.float64)


def _reindex_simplices(original: NDArray[np.integer], new_pointset: IntArray) -> IntArray:
    reindex = {int(value): index for index, value in enumerate(new_pointset.tolist())}
    return np.asarray([[reindex[int(point)] for point in simplex] for simplex in original], dtype=np.int64)


def _build_half_hull(convex_hull: ConvexHull, simplex_indices: IntArray, axis: int) -> HalfConvexHull:
    point_indices = np.unique(convex_hull.simplices[simplex_indices].reshape(-1)).astype(np.int64)
    simplices = _reindex_simplices(convex_hull.simplices[simplex_indices].astype(np.int64), point_indices)
    return HalfConvexHull(
        points=np.asarray(convex_hull.points[point_indices], dtype=np.float64),
        simplices=simplices,
        axis=axis,
        equations=np.asarray(convex_hull.equations[simplex_indices], dtype=np.float64),
        original_indices=point_indices,
    )


def get_lower_upper_qhull(
    convex_hull: ConvexHull,
    axis: int = 0,
    case_2d: str = "rate_ps",
) -> tuple[HalfConvexHull, HalfConvexHull, HalfConvexHull | None]:
    """Split a convex hull's facets into the half below (lower) and above (upper) the
    hyperplane orthogonal to axis through the hull's centre, plus (when applicable, see
    below) the "upper monotonic" subset of the upper half whose facets are monotonic in
    the two other axes - used to build single-valued 1D boundary functions for
    extrapolation outside the hull.
    """
    test_point = (convex_hull.max_bound + convex_hull.min_bound) / 2
    non_boundary = np.flatnonzero(convex_hull.equations[:, axis] != 0.0)
    normalized = convex_hull.equations[non_boundary] / convex_hull.equations[non_boundary, axis].reshape(-1, 1)
    other_axes = [index for index in range(convex_hull.ndim) if index != axis]
    test_values = -normalized[:, -1]
    for other_axis in other_axes:
        test_values -= normalized[:, other_axis] * test_point[other_axis]
    upper_indices = non_boundary[test_values >= test_point[axis]].astype(np.int64)
    lower_indices = non_boundary[test_values <= test_point[axis]].astype(np.int64)
    lower = _build_half_hull(convex_hull, lower_indices, axis)
    upper = _build_half_hull(convex_hull, upper_indices, axis)

    monotonic_indices: IntArray | None = None
    build_monotonic = False
    if axis == 0:
        upper_normalized = convex_hull.equations[upper_indices] / convex_hull.equations[upper_indices, axis].reshape(
            -1, 1
        )
        if convex_hull.ndim == 3:
            build_monotonic = True
            monotonic_mask = np.logical_and(upper_normalized[:, 1] <= 0, upper_normalized[:, 2] >= 0)
            monotonic_indices = upper_indices[np.flatnonzero(monotonic_mask)].astype(np.int64)
        elif convex_hull.ndim == 2 and case_2d in ("rate_ps", "rate_pd"):
            build_monotonic = True
            monotonic_mask = upper_normalized[:, 1] <= 0 if case_2d == "rate_ps" else upper_normalized[:, 1] >= 0
            monotonic_indices = upper_indices[np.flatnonzero(monotonic_mask)].astype(np.int64)

    # Unlike lower/upper, the "upper monotonic" half hull is only defined for axis 0 and
    # for the case_2d values above (matching legacy's do_monotonic flag): it is None when
    # not applicable, but a (possibly empty) HalfConvexHull whenever it is, even if no
    # facet happens to satisfy the monotonicity condition for the given sample data.
    monotonic = _build_half_hull(convex_hull, cast(IntArray, monotonic_indices), axis) if build_monotonic else None
    return lower, upper, monotonic


class LinearSurfaceInterpolator:
    """Evaluate the value of one axis (e.g. rate) as a function of the other two, on the
    surface of a half convex hull's simplices.

    scipy's LinearNDInterpolator triangulates its own input points and its triangulation
    may not preserve the surface of the simplices already defined by the (outer) convex
    hull - so instead this walks the half hull's own simplices directly and solves each
    one's hyperplane equation for the function axis. Points that fall outside every
    simplex of the half hull (e.g. due to floating-point edge effects) fall back to a
    LinearNDInterpolator built from the half hull's own points.
    """

    def __init__(
        self,
        half_convex_hull: HalfConvexHull,
        fill_value: float = np.nan,
    ) -> None:
        self._half_convex_hull = half_convex_hull
        self._function_axis = half_convex_hull.axis
        self._variable_axes = [index for index in range(half_convex_hull.ndim) if index != half_convex_hull.axis]
        self._simplices = half_convex_hull.points[half_convex_hull.simplices][:, :, self._variable_axes]
        self._equations = half_convex_hull.equations
        self._fallback_function = LinearNDInterpolator(
            half_convex_hull.points[:, self._variable_axes],
            half_convex_hull.points[:, self._function_axis],
            fill_value=fill_value,
            rescale=False,
        )

    def __call__(self, *args: FloatArray) -> FloatArray:
        variable_array = args[0] if len(args) == 1 else np.stack(args, axis=-1)
        return self.evaluate(variable_array)

    @staticmethod
    def _cross_2d(first: FloatArray, second: FloatArray) -> FloatArray:
        return first[:, 0] * second[:, 1] - first[:, 1] * second[:, 0]

    @classmethod
    def _points_inside_simplex(cls, points: FloatArray, simplex: FloatArray) -> IntArray:
        a, b, c = simplex

        def check_side(start: FloatArray, end: FloatArray, ref: FloatArray) -> FloatArray:
            relative = points - ref
            return cls._cross_2d(np.tile(start, (points.shape[0], 1)), relative) * cls._cross_2d(
                np.tile(start, (points.shape[0], 1)),
                np.tile(end, (points.shape[0], 1)),
            )

        inside = np.ones(points.shape[0], dtype=bool)
        inside[check_side(c - b, a - b, b) < 0] = False
        inside[check_side(c - a, b - a, a) < 0] = False
        inside[check_side(b - a, c - a, a) < 0] = False
        return np.flatnonzero(inside).astype(np.int64)

    def _evaluate_surface(self, equation: FloatArray, variable_array: FloatArray) -> FloatArray:
        """Solve the simplex's hyperplane equation (sum(coefficient * axis_value) +
        offset = 0) for the function axis, given the other axes' values."""
        result = np.full(variable_array.shape[0], np.nan)
        coefficient = equation[self._function_axis]
        if coefficient == 0:
            return result
        result.fill(-equation[-1])
        for variable_index, axis in enumerate(self._variable_axes):
            result -= equation[axis] * variable_array[:, variable_index]
        result /= coefficient
        return result

    def evaluate(self, variable_array: FloatArray) -> FloatArray:
        if variable_array.shape[1] != len(self._variable_axes):
            raise ValueError(
                f"Expected {len(self._variable_axes)} columns in variable_array, got {variable_array.shape[1]}."
            )
        result = np.full(variable_array.shape[0], np.nan)
        for simplex, equation in zip(self._simplices, self._equations, strict=True):
            indices = self._points_inside_simplex(variable_array, simplex)
            if indices.size:
                result[indices] = self._evaluate_surface(equation, variable_array[indices])
        missing = np.flatnonzero(np.isnan(result))
        if missing.size:
            result[missing] = np.asarray(self._fallback_function(variable_array[missing]), dtype=np.float64)
        return result


__all__ = [
    "FloatArray",
    "HalfConvexHull",
    "IntArray",
    "LinearSurfaceInterpolator",
    "get_lower_upper_qhull",
    "sort_ndarray_by_column",
]
