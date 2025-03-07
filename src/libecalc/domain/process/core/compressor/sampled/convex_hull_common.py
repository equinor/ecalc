from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from scipy.interpolate import LinearNDInterpolator
from scipy.spatial import ConvexHull

from libecalc.common.logger import logger


def sort_ndarray_by_column(arr: NDArray[np.float64], column_index: NDArray[np.float64]) -> NDArray[np.float64]:
    """Sort array by column index

    Args:
        arr: Array to be sorted
        column_index: column index to sort by

    Returns:
        array sorted by column

    """
    return np.array(arr[arr[:, column_index].argsort()])


@dataclass
class Node:
    coordinates: list[float]

    def scale(self, scale_factors):
        coords_scaled = [self.coordinates[idx] / scale_factors[idx] for idx in range(len(self.coordinates))]
        return Node(coordinates=coords_scaled)


@dataclass
class HalfConvexHull:
    points: NDArray[np.float64]
    simplices: NDArray[np.float64]
    axis: int
    equations: NDArray[np.float64]
    original_qhull_indices: NDArray[np.float64] | None = None
    neighbors: NDArray[np.float64] | None = None

    @property
    def nsimplex(self) -> int:
        return self.simplices.shape[0]

    @property
    def npoints(self) -> int:
        return self.points.shape[0]

    @property
    def ndim(self) -> int:
        return self.points.shape[1]

    def reorder_axes(self, axis: int, variable_axes: list):
        new_axes = [axis] + variable_axes
        points_reordered = self.points[:, new_axes]
        equations_reordered = self.equations[:, new_axes + [-1]]
        return HalfConvexHull(
            points=points_reordered,
            simplices=self.simplices,
            axis=0,
            equations=equations_reordered,
        )

    @property
    def vertices(self):
        return np.unique(self.simplices)


def _compute_simplices_in_new_pointset(
    original_simplices: NDArray[np.float64],
    new_pointset: NDArray[np.float64],
    default: float = -999,
):
    """Simplices for a ConvexHull object refers to indices of the points with coordinates defined in the "points"
    attribute. When a subset of the points in a ConvexHull object is returned (e.g. the points of the upper or lower
    qhull), the corresponding simplices attribute must refer to the indices of the points in the new points set.
    """
    reindex_map = {value: index for index, value in enumerate(new_pointset)}
    simplices_reindexed = np.asarray(
        list(
            map(
                np.vectorize(lambda x: reindex_map.get(x, default)),
                original_simplices,
            )
        )
    )

    return simplices_reindexed


"""
Split points of convex hull into three parts - pure upper simplices, pure lower simplices and boundary simplices
Return as point sets for upper and lower
axis: The axis along upper and lower is defined
"""


def get_lower_upper_qhull(qh: ConvexHull, axis: int = 0, case_2d: str = "rate_ps"):
    """This function returns the upper and lower part of a convex hull with respect
    to the direction defined by axis.
    It also return the part of the upper convex hull where the first variable is
    monotonically increasing when the second variable is increasing and the third
    variable is decreasing.
    These functions are used for further computation of functions to be used for
    projection of (rate, ps, pd) points.
    """
    # Select one point in the middle of the convex hull
    test_point = (qh.max_bound + qh.min_bound) / 2

    non_boundary_simplices = np.argwhere(qh.equations[:, axis] != 0.0)[:, 0]
    eqs_non_boundary_unified = qh.equations[non_boundary_simplices, :] / qh.equations[
        non_boundary_simplices, axis
    ].reshape(-1, 1)

    eval_axes = [x for x in range(qh.ndim) if x != axis]
    test_values = -1 * eqs_non_boundary_unified[:, -1]
    for ax in eval_axes:
        test_values -= eqs_non_boundary_unified[:, ax] * test_point[ax]

    # The upper simplices are the ones with hyperplane test value larger than the internal point
    # The lower simplices are the ones with hyperplane test values smaller
    upper_simplices_indices = non_boundary_simplices[test_values >= test_point[axis]]
    lower_simplices_indices = non_boundary_simplices[test_values <= test_point[axis]]

    # Find the points of the upper and lower simplices
    upper_point_indices = np.unique(qh.simplices[upper_simplices_indices, :].reshape(-1, 1))
    lower_point_indices = np.unique(qh.simplices[lower_simplices_indices, :].reshape(-1, 1))

    # Find the coordinates of the upper and lower points
    upper_points = qh.points[upper_point_indices, :]
    lower_points = qh.points[lower_point_indices, :]

    lower_simplices = qh.simplices[lower_simplices_indices, :]
    lower_simplices_indexed_to_new_pointset = _compute_simplices_in_new_pointset(
        original_simplices=lower_simplices, new_pointset=lower_point_indices
    )
    lower_equations = qh.equations[lower_simplices_indices, :]
    upper_simplices = qh.simplices[upper_simplices_indices, :]
    upper_simplices_indexed_to_new_pointset = _compute_simplices_in_new_pointset(
        original_simplices=upper_simplices, new_pointset=upper_point_indices
    )
    upper_equations = qh.equations[upper_simplices_indices, :]

    lower_neighbors = _compute_simplices_in_new_pointset(
        original_simplices=qh.neighbors[lower_simplices_indices, :],
        new_pointset=lower_simplices_indices,
    )

    upper_neighbors = _compute_simplices_in_new_pointset(
        original_simplices=qh.neighbors[upper_simplices_indices, :],
        new_pointset=upper_simplices_indices,
    )

    lower_qh = HalfConvexHull(
        points=lower_points,
        simplices=lower_simplices_indexed_to_new_pointset,
        equations=lower_equations,
        axis=axis,
        original_qhull_indices=lower_point_indices,
        neighbors=lower_neighbors,
    )
    upper_qh = HalfConvexHull(
        points=upper_points,
        simplices=upper_simplices_indexed_to_new_pointset,
        equations=upper_equations,
        axis=axis,
        original_qhull_indices=upper_point_indices,
        neighbors=upper_neighbors,
    )

    # Currently only supported for 3D and axis=0
    if axis == 0:
        if qh.ndim == 3:
            """
            Find the data among upper where rate is monotonically increasing for decreasing pd and increasing ps
            Note that it is assumed that rate is the first variable, ps is the second and pd the third.
            The data is the data among upper where the first axis is monotonically increasing for increasing
            second variable and decreasing third variable
            Needed for max rate functionality
            """
            eq_upper = qh.equations[upper_simplices_indices, :] / qh.equations[upper_simplices_indices, axis].reshape(
                -1, 1
            )
            upper_monotonic_correct_simplices_indices = upper_simplices_indices[
                np.argwhere((eq_upper[:, 1] <= 0) & (eq_upper[:, 2] >= 0))[:, 0]
            ]
            upper_monotonic_correct_point_indices = np.unique(
                qh.simplices[upper_monotonic_correct_simplices_indices, :].reshape(-1, 1)
            )
            upper_monotonic_correct_points = qh.points[upper_monotonic_correct_point_indices, :]
            upper_monotonic_correct_neighbors = _compute_simplices_in_new_pointset(
                original_simplices=qh.neighbors[upper_monotonic_correct_simplices_indices, :],
                new_pointset=upper_monotonic_correct_simplices_indices,
            )

        elif qh.ndim == 2:
            do_monotonic = True
            upper_monotonic_correct_neighbors = None
            eq_upper = qh.equations[upper_simplices_indices, :] / qh.equations[upper_simplices_indices, axis].reshape(
                -1, 1
            )
            if case_2d == "rate_ps":
                """
                The first axis is rate and the second is ps
                Find the data among upper where rate is monotonically increasing for increasing ps
                """
                upper_monotonic_correct_simplices_indices = upper_simplices_indices[
                    np.argwhere(eq_upper[:, 1] <= 0)[:, 0]
                ]
            elif case_2d == "rate_pd":
                """
                The first axis is rate and the second is pd
                Find the data among upper where rate is monotonically increasing for decreasing pd
                """
                upper_monotonic_correct_simplices_indices = upper_simplices_indices[
                    np.argwhere(eq_upper[:, 1] >= 0)[:, 0]
                ]  # BUG? copy paste, Check if eq_upper[:, 2] should be eq_upper[:, 1], only have two dimensions
            else:
                do_monotonic = False
                upper_monotonic_correct_points = None
            if do_monotonic:
                upper_monotonic_correct_point_indices = np.unique(
                    qh.simplices[upper_monotonic_correct_simplices_indices, :].reshape(-1, 1)
                )
                upper_monotonic_correct_points = qh.points[upper_monotonic_correct_point_indices, :]
    else:
        upper_monotonic_correct_points = None

    if upper_monotonic_correct_points is not None:
        upper_monotonic_correct_simplices = qh.simplices[upper_monotonic_correct_simplices_indices, :]
        upper_monotonic_correct_simplices_indexed_to_new_pointset = _compute_simplices_in_new_pointset(
            original_simplices=upper_monotonic_correct_simplices,
            new_pointset=upper_monotonic_correct_point_indices,
        )
        upper_monotonic_correct_equations = qh.equations[upper_monotonic_correct_simplices_indices, :]

        upper_monotonic_correct_qh = HalfConvexHull(
            points=upper_monotonic_correct_points,
            simplices=upper_monotonic_correct_simplices_indexed_to_new_pointset,
            equations=upper_monotonic_correct_equations,
            axis=axis,
            original_qhull_indices=upper_monotonic_correct_point_indices,
            neighbors=upper_monotonic_correct_neighbors,
        )
    else:
        upper_monotonic_correct_qh = None

    return lower_qh, upper_qh, upper_monotonic_correct_qh


class Simplex:
    def __init__(
        self,
        nodes: list[Node],
        equation_coefficients: NDArray[np.float64],
        rescale: bool = True,
    ):
        self.nodes = nodes

        self._ndim = len(nodes[0].coordinates)
        if rescale:
            self._scale_factors = [
                max([node.coordinates[coordidx] for node in nodes]) for coordidx in range(self._ndim)
            ]
            nodes_scaled = [node.scale(self._scale_factors) for node in nodes]
            self._equation = self._calculate_plane_equation(nodes=nodes_scaled)
        else:
            self._scale_factors = np.full(shape=self._ndim, fill_value=1.0).tolist()
            self._equation = equation_coefficients

    @staticmethod
    def _calculate_plane_equation(nodes: list[Node]) -> NDArray[np.float64]:
        """Calculate equation of plane going through three points in 3D
        https://mathworld.wolfram.com/Plane.html
        Returns array with 4 coefficients, [a, b, c, d]
        Equation of plane is a*x+b*y+c*z+d=0.
        """
        p1 = np.asarray(nodes[0].coordinates)
        p2 = np.asarray(nodes[1].coordinates)
        p3 = np.asarray(nodes[2].coordinates)
        v1 = p1 - p3
        v2 = p2 - p3
        n = np.cross(v1, v2)
        d = np.dot(n, p1)
        equation = np.append(n, -d)
        return equation

    def evaluate_surface(self, function_axis: int, variables_to_evaluate: NDArray[np.float64]):
        """Evaluate surface (plane) equation to find value in "function_axis" direction
        for "variables_to_evaluate" in the other directions.
        See https://mathworld.wolfram.com/Hyperplane.html for equations.

        Surface equation for plane in 3D: a*x+b*y+c*z+d=0
        function_axis refers to one axis, e.g. 0 for x, 1 for y and 2 for z
        variables_to_evaluate contains variables for the other directions,
        e.g. if function_axis is 0 (x), variables_to_evaluate will contain
        y and z values. Thus to solve for x:
        x = - (d+b*y+c*z)/a
        Correspondingly if function_axis is 1(y) or 2(z)
        y =  - (d+a*x+c*z)/b
        z =  - (d+a*x+b*y)/c
        """
        # May only evaluate if coefficient is not 0 in function_axis direction
        if self._equation[function_axis] == 0:
            return np.full(variables_to_evaluate.shape[0], np.nan)

        # Find axes with variables (those which are not function_axis)
        eval_axes = [x for x in range(self._ndim) if x != function_axis]

        # Unify equations such that one may solve for variable in function_axis direction,
        # e.g. x = - (d+b*y+c*z)/a if function_axis is 0
        # self._equations have coefficients [a,b,c,d]
        # unified equation will then contain coefficients [-1,-b/a,-c/a,-d/a] such that
        # x may be solved(added up) in steps as x = (-d/a) + (-b/a) * y + (-c/a) * z
        # y and z are given as y = variables_to_evaluate[0], z = variables_to_evaluate[1]
        equation_unified = -1.0 * self._equation / self._equation[function_axis]
        # Add constant coefficient
        evaluated = equation_unified[-1]
        # Add coefficient * variable value along axis in all directions
        variables_to_evaluate_index = 0
        for ax in eval_axes:
            evaluated += (
                equation_unified[ax] * variables_to_evaluate[:, variables_to_evaluate_index] / self._scale_factors[ax]
            )
            variables_to_evaluate_index += 1

        evaluated_unscaled = evaluated * self._scale_factors[function_axis]

        return evaluated_unscaled


class LinearInterpolatorSimplicesDefined:
    """Linear interpolation on a set of simplices.
    Used to evaluate surface of part of a convex hull.
    (scipy.LinearNDInterpolator may have a triangulation which does not preserve the surface of the
    vertices defined in a convex hull at higher level).
    """

    def __init__(
        self,
        half_convex_hull: HalfConvexHull,
        fill_value: float = np.nan,
        rescale: bool = False,
        fill_convex_hull: bool = True,
    ) -> None:
        if not isinstance(half_convex_hull, HalfConvexHull):
            msg = "half_convex_hull is not of type HalfConvexHull"
            logger.error(msg)
            raise TypeError(msg)
        self._half_convex_hull = half_convex_hull
        self._function_value_axis = half_convex_hull.axis
        self._variable_axes = [x for x in range(half_convex_hull.ndim) if x != half_convex_hull.axis]
        self._ndim = half_convex_hull.ndim - 1
        self._simplices = self._setup_simplices_from_qhulltable(
            simplex_table=half_convex_hull.simplices,
            equations_table=half_convex_hull.equations,
            points_table=half_convex_hull.points,
            rescale=rescale,
        )

        self._fill_value = fill_value

        self._fill_convex_function = None
        if fill_convex_hull:
            self._fill_convex_function = LinearNDInterpolator(
                points=half_convex_hull.points[:, [1, 2]],
                values=half_convex_hull.points[:, 0],
                rescale=False,
                fill_value=self._fill_value,
            )

    def __call__(self, *args):
        """To be consistent with scipy.LinearNDInterpolator. Either one ndarray with all
        variables or one ndarray for each variable.
        """
        if len(args) == 1:
            return self.evaluate(variable_array=args[0])
        elif len(args) == self._ndim:
            variable_array = np.stack(args, axis=-1)
            return self.evaluate(variable_array=variable_array)

    @staticmethod
    def _setup_simplices_from_qhulltable(
        simplex_table: NDArray[np.float64],
        equations_table: NDArray[np.float64],
        points_table: NDArray[np.float64],
        rescale: bool = True,
    ) -> list[Simplex]:
        simplices = []
        for row in range(simplex_table.shape[0]):
            point_list = simplex_table[row, :]
            simplex_point_list = [Node(points_table[point_list[index]]) for index in range(3)]
            simplex = Simplex(
                nodes=simplex_point_list,
                equation_coefficients=equations_table[row, :],
                rescale=rescale,
            )
            simplices.append(simplex)
        return simplices

    @staticmethod
    def _points_inside_simplex(
        points: NDArray[np.float64],
        simplex_point1: NDArray[np.float64],
        simplex_point2: NDArray[np.float64],
        simplex_point3: NDArray[np.float64],
    ) -> NDArray[np.float64]:
        """Method to find indices of points inside a simplex.

        Input:
        points: points to evaluate. ndarray in two dimensions where each row defines a point to evaluate
        simplex_point<n>: points that define the simplex. ndarray in one dimension

        Returns:
        Indices of points which are inside simplex. ndarray with int64.
        """
        input_points_is_inside_simplex: NDArray[np.float64] = LinearInterpolatorSimplicesDefined._is_inside(
            p=points, a=simplex_point1, b=simplex_point2, c=simplex_point3
        )

        input_points_inside_simplex_indices = np.argwhere(input_points_is_inside_simplex > 0)[:, 0]
        return input_points_inside_simplex_indices

    @staticmethod
    def _is_inside(
        p: NDArray[np.float64], a: NDArray[np.float64], b: NDArray[np.float64], c: NDArray[np.float64]
    ) -> NDArray[np.float64]:
        """Method to evaluate if points are inside a given simplex.

        checks which of the points in p is inside the triangle defined by points a, b, c

        Input:
        a, b, c: points which defines a simplex (triangle). Each of these is a ndarray in one dimension
        p: table points to evaluate. ndarray in two dimension, each row defines a point to evaluate.

        Returns:
        A vector with length equal to number of points in p
        with value 1 for points inside the simplex defined by a, b. c
        and 0 for points outside
        """
        cp1 = np.cross(c - b, p - b)
        cp2 = np.cross(c - b, a - b)
        ss1 = np.dot(cp1, cp2)
        cp1 = np.cross(c - a, p - a)
        cp2 = np.cross(c - a, b - a)
        ss2 = np.dot(cp1, cp2)
        cp1 = np.cross(b - a, p - a)
        cp2 = np.cross(b - a, c - a)
        ss3 = np.dot(cp1, cp2)

        inside = np.ones(p.shape[0])
        inside[np.argwhere(ss1 < 0)[:, 0]] = 0
        inside[np.argwhere(ss2 < 0)[:, 0]] = 0
        inside[np.argwhere(ss3 < 0)[:, 0]] = 0

        return inside

    def evaluate(self, variable_array: NDArray[np.float64]) -> NDArray[np.float64]:
        if variable_array.shape[1] != self._ndim:
            msg = "variable_array.shape[1] does not match self._ndim"
            logger.error(msg)
            raise ValueError(msg)

        # Go through simplices and points to check which simplex a point belongs to
        fill_value = self._fill_value if self._fill_convex_function is None else np.nan
        result = np.full(variable_array.shape[0], fill_value)

        for simplex in self._simplices:
            input_points_inside_simplex_indices = self._points_inside_simplex(
                points=variable_array,
                simplex_point1=np.array(simplex.nodes[0].coordinates)[self._variable_axes],
                simplex_point2=np.array(simplex.nodes[1].coordinates)[self._variable_axes],
                simplex_point3=np.array(simplex.nodes[2].coordinates)[self._variable_axes],
            )

            result[input_points_inside_simplex_indices] = simplex.evaluate_surface(
                function_axis=self._function_value_axis,
                variables_to_evaluate=variable_array[input_points_inside_simplex_indices],
            )

        """
        Sometimes the half convex hull is just a part of the original half hull
        e.g. only part of original half hull with certain gradients (monotonic correct)
        In this case, the interpolation over all simplices does not cover the entire convex area
        of the evaluation points. The points not covered, will be approximated with LinearNDInterpolation
        """
        if self._fill_convex_function is not None:
            nan_value_indices = np.argwhere(np.isnan(result))[:, 0]
            if len(nan_value_indices) > 0:
                result[nan_value_indices] = self._fill_convex_function(variable_array[nan_value_indices, :])
        return result
