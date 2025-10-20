from pathlib import Path

import numpy as np
import pandas as pd
from scipy.spatial import ConvexHull

from libecalc.domain.process.compressor.sampled.compressor_model_sampled_3d import (
    CompressorModelSampled3D,
)
from libecalc.domain.process.compressor.sampled.constants import (
    PD_NAME,
    PS_NAME,
    RATE_NAME,
)
from libecalc.domain.process.compressor.sampled.convex_hull_common import (
    HalfConvexHull,
    LinearInterpolatorSimplicesDefined,
    Node,
    Simplex,
    _compute_simplices_in_new_pointset,
    get_lower_upper_qhull,
)

VARIABLE_ORDER_3D = [RATE_NAME, PS_NAME, PD_NAME]


def test_get_lower_upper_qhull():
    # 3D tests

    # Cube with "hat". No common points in upper and lower in axis 0
    df_data = np.asarray(
        [[2, 1, 1], [2, 1, 3], [2, 3, 1], [2, 3, 3], [3, 2, 2], [1, 1, 1], [1, 1, 3], [1, 3, 1], [1, 3, 3]]
    )

    df = pd.DataFrame(df_data)

    variables = VARIABLE_ORDER_3D

    # func_header = EcalcYamlKeywords.consumer_tabular_fuel
    df.columns = variables  # + [func_header]

    qh = ConvexHull(df[variables][:].values)

    # Test in all three directions
    lower_p, upper_p, _ = get_lower_upper_qhull(qh, axis=0)
    np.testing.assert_allclose(lower_p.points, df_data[5:])
    np.testing.assert_allclose(upper_p.points, df_data[:5])

    lower_p, upper_p, _ = get_lower_upper_qhull(qh, axis=1)
    np.testing.assert_allclose(lower_p.points, df_data[[0, 1, 4, 5, 6]])
    np.testing.assert_allclose(upper_p.points, df_data[[2, 3, 4, 7, 8]])

    lower_p, upper_p, _ = get_lower_upper_qhull(qh, axis=2)
    np.testing.assert_allclose(lower_p.points, df_data[[0, 2, 4, 5, 7]])
    np.testing.assert_allclose(upper_p.points, df_data[[1, 3, 4, 6, 8]])

    # Common boundary points in axis 0
    df_data = np.asarray(
        [
            [2, 2, 2],
            [2, 2, 3],
            [2, 3, 2],
            [2, 3, 3],
            [1, 1, 1],
            [1, 1, 4],
            [1, 4, 1],
            [1, 4, 4],
            [0, 2, 2],
            [0, 2, 3],
            [0, 3, 2],
            [0, 3, 3],
        ]
    )
    df = pd.DataFrame(df_data)

    variables = VARIABLE_ORDER_3D

    df.columns = variables

    qh = ConvexHull(df[variables][:].values)

    # axis=0
    lower_p, upper_p, _ = get_lower_upper_qhull(qh, axis=0)
    np.testing.assert_allclose(lower_p.points, df_data[4:])
    np.testing.assert_allclose(upper_p.points, df_data[:8])

    # axis=1
    lower_p, upper_p, _ = get_lower_upper_qhull(qh, axis=1)
    np.testing.assert_allclose(lower_p.points, df_data[[0, 1, 4, 5, 8, 9]])
    np.testing.assert_allclose(upper_p.points, df_data[[2, 3, 6, 7, 10, 11]])

    # axis=2
    lower_p, upper_p, _ = get_lower_upper_qhull(qh, axis=2)
    np.testing.assert_allclose(lower_p.points, df_data[[0, 2, 4, 6, 8, 10]])
    np.testing.assert_allclose(upper_p.points, df_data[[1, 3, 5, 7, 9, 11]])

    df_data_full = np.asarray(
        [
            [1000000, 50, 162, 52765],  # 0
            [1000000, 50, 258, 76928],
            [1000000, 50, 394, 118032],
            [1000000, 50, 471, 145965],
            [3000000, 50, 237, 71918],
            [3000000, 50, 258, 109823],  # 5
            [3000000, 50, 449, 137651],
            [7000000, 50, 322, 139839],
            [1000000, 51, 166, 53000],
            [1000000, 51, 480, 148000],
            [1000000, 52, 171, 54441],  # 10
            [1000000, 52, 215, 65205],
            [1000000, 52, 336, 98692],
            [1000000, 52, 487, 151316],
            [3000000, 52, 249, 74603],
            [3000000, 52, 384, 114277],  # 15
            [3000000, 52, 466, 143135],
            [7200000, 52, 362, 144574],
        ]
    )
    df_data = df_data_full[:, :3]
    df = pd.DataFrame(df_data)
    df.columns = variables

    qh = ConvexHull(df[variables][:].values)

    # axis=0
    lower_p, upper_p, _ = get_lower_upper_qhull(qh, axis=0)
    np.testing.assert_allclose(lower_p.points, df_data[[0, 3, 8, 9, 10, 13]])
    np.testing.assert_allclose(upper_p.points, df_data[[0, 3, 6, 7, 8, 9, 10, 13, 16, 17]])

    # 2D tests
    df_data = np.asarray([[1, 2], [2, 1], [2, 3], [3, 2]])
    qh = ConvexHull(df_data)

    lower_p, upper_p, _ = get_lower_upper_qhull(qh, axis=0)
    np.testing.assert_allclose(lower_p.points, df_data[:3])
    np.testing.assert_allclose(upper_p.points, df_data[1:])

    lower_p, upper_p, _ = get_lower_upper_qhull(qh, axis=1)
    np.testing.assert_allclose(lower_p.points, df_data[[0, 1, 3]])
    np.testing.assert_allclose(upper_p.points, df_data[[0, 2, 3]])

    df_data = np.asarray([[1, 2], [1, 3], [2, 1], [2, 4], [3, 1], [3, 4], [4, 2], [4, 3]])
    qh = ConvexHull(df_data)

    lower_p, upper_p, _ = get_lower_upper_qhull(qh, axis=0)
    np.testing.assert_allclose(lower_p.points, df_data[:4])
    np.testing.assert_allclose(upper_p.points, df_data[4:])
    lower_p, upper_p, _ = get_lower_upper_qhull(qh, axis=1)
    np.testing.assert_allclose(lower_p.points, df_data[[0, 2, 4, 6]])
    np.testing.assert_allclose(upper_p.points, df_data[[1, 3, 5, 7]])


def test_compute_simplices_in_new_pointset():
    original_simplices = np.asarray([[16, 8, 0], [16, 31, 0], [15, 8, 0], [25, 16, 8], [25, 16, 31], [7, 15, 0]])
    new_pointset = np.asarray([0, 7, 8, 15, 16, 25, 31])

    simplices_new_pointset = _compute_simplices_in_new_pointset(
        original_simplices=original_simplices, new_pointset=new_pointset
    )

    expected = np.asarray([[4, 2, 0], [4, 6, 0], [3, 2, 0], [5, 4, 2], [5, 4, 6], [1, 3, 0]])

    np.testing.assert_equal(expected, simplices_new_pointset)


def test_Node_scale():
    node1 = Node(coordinates=[10, 20, 1000])
    node2 = Node(coordinates=[10, 20, 1000])

    scale_factors = [20, 20, 2000]

    node1_scaled = node1.scale([20, 20, 2000])
    node2_scaled = node2.scale([20, 20, 2000])
    node3_scaled = node1.scale(np.asarray(scale_factors))
    node4_scaled = node2.scale(np.asarray(scale_factors))

    expected = [0.5, 1.0, 0.5]

    np.testing.assert_allclose(expected, node1_scaled.coordinates)
    np.testing.assert_allclose(expected, node2_scaled.coordinates)
    np.testing.assert_allclose(expected, node3_scaled.coordinates)
    np.testing.assert_allclose(expected, node4_scaled.coordinates)


def test_calculate_plane_equation():
    node1 = Node(coordinates=[2, 1, 1])
    node2 = Node(coordinates=[1, 2, 2])
    node3 = Node(coordinates=[3, 2, 2])

    equation = Simplex._calculate_plane_equation([node1, node2, node3])

    # Should be on plane. First three are coordinates,
    # last is 1 for adding constant
    test_point = np.asarray([2, 1.5, 1.5, 1])
    assert np.dot(test_point, equation) == 0

    node1 = Node(coordinates=[1, 1, 2])
    node2 = Node(coordinates=[2, 1, 3])
    node3 = Node(coordinates=[1, 2, 4])

    equation = Simplex._calculate_plane_equation([node1, node2, node3])

    # Should be on plane. First three are coordinates,
    # last is 1 for adding constant
    test_point = np.asarray([1.5, 1.5, 3.5, 1])
    assert np.dot(test_point, equation) == 0


def test_simplex_evaluate_surface():
    node1 = Node(coordinates=[5, 1, 2])
    node2 = Node(coordinates=[5, 2, 1])
    node3 = Node(coordinates=[4, 4, 2])
    node4 = Node(coordinates=[3, 3, 3])
    equation = Simplex._calculate_plane_equation([node1, node2, node3])
    np.testing.assert_allclose(equation, [3, 1, 1, -18])

    simplex = Simplex([node1, node2, node3, node4], equation)
    ps_pd = np.asarray([[2, 2]])
    result = simplex.evaluate_surface(0, ps_pd)
    np.testing.assert_allclose(result, np.divide(14, 3))
    ps_pd = np.asarray([[1.75, 2.75]])
    result = simplex.evaluate_surface(0, ps_pd)
    np.testing.assert_allclose(result, 4.5)
    rate_pd = np.asarray([[2, 3]])
    result = simplex.evaluate_surface(1, rate_pd)
    np.testing.assert_allclose(result, 9)

    rate_ps = np.asarray([[2, 3]])
    result = simplex.evaluate_surface(2, rate_ps)
    np.testing.assert_allclose(result, 9)


def test_setup_simplices_from_qhulltable():
    lower_rate_points = np.asarray([[1, 2, 6], [2, 1, 3], [2, 5, 7], [3, 4, 4], [4, 3, 1], [4, 7, 5], [5, 6, 2]])

    lower_rate_simplices = np.asarray([[1, 2, 0], [1, 6, 5], [1, 6, 4], [1, 2, 5]])
    lower_rate_equations = np.asarray(
        [
            [-0.81649658, 0.40824829, -0.40824829, 2.44948974],
            [-0.81649658, 0.40824829, -0.40824829, 2.44948974],
            [-0.81649658, 0.40824829, -0.40824829, 2.44948974],
            [-0.81649658, 0.40824829, -0.40824829, 2.44948974],
        ]
    )
    simplices_from_qhulltable = LinearInterpolatorSimplicesDefined._setup_simplices_from_qhulltable(
        lower_rate_simplices, lower_rate_equations, lower_rate_points
    )

    np.testing.assert_allclose(simplices_from_qhulltable[0].nodes[0].coordinates, [2, 1, 3])
    np.testing.assert_allclose(simplices_from_qhulltable[0].nodes[1].coordinates, [2, 5, 7])
    np.testing.assert_allclose(simplices_from_qhulltable[3].nodes[0].coordinates, [2, 1, 3])
    np.testing.assert_allclose(simplices_from_qhulltable[2].nodes[1].coordinates, [5, 6, 2])

    lower_rate_points = np.asarray([[1, 1, 1], [1, 1, 2], [4, 2, 1]])

    lower_rate_simplices = np.asarray([[1, 2, 0]])
    lower_rate_equations = np.asarray([[1, 1, 1, 1]])

    simplices_from_qhulltable = LinearInterpolatorSimplicesDefined._setup_simplices_from_qhulltable(
        lower_rate_simplices, lower_rate_equations, lower_rate_points
    )

    np.testing.assert_allclose(simplices_from_qhulltable[0]._equation, [-0.25, 0.375, 0, -0.125])


def test_linear_interpolation_simplices_defined():
    lower_rate_points = np.asarray([[1, 2, 6], [2, 1, 3], [2, 5, 7], [3, 4, 4], [4, 3, 1], [4, 7, 5], [5, 6, 2]])

    lower_rate_simplices = np.asarray([[1, 2, 0], [1, 6, 5], [1, 6, 4], [1, 2, 5]])
    lower_rate_equations = np.asarray(
        [
            [-0.81649658, 0.40824829, -0.40824829, 2.44948974],
            [-0.81649658, 0.40824829, -0.40824829, 2.44948974],
            [-0.81649658, 0.40824829, -0.40824829, 2.44948974],
            [-0.81649658, 0.40824829, -0.40824829, 2.44948974],
        ]
    )

    lower_rate_qh = HalfConvexHull(
        points=lower_rate_points,
        simplices=lower_rate_simplices,
        axis=0,
        equations=lower_rate_equations,
    )
    min_rate_function = LinearInterpolatorSimplicesDefined(lower_rate_qh)
    ps_pd = np.asarray([[3, 1], [2.5, 3.5], [7.05, 4], [5, 0.9], [4, 2], [3.5, 5.5]])
    res = min_rate_function(ps_pd)
    np.testing.assert_allclose(res, [4, 2.5, np.nan, np.nan, 4, 2])


def test_equation_of_plane():
    equation = Simplex._calculate_plane_equation([Node([1, 0, 0]), Node([0, 1, 0]), Node([0, 0, 1])])
    np.testing.assert_allclose(equation, [1, 1, 1, -1])


def test_sampled_compressor_datedata2():
    testfile = Path(__file__).parent / "input" / "compressor_sampled_3d_vsd_testdata2.csv"
    df = pd.read_csv(testfile, comment="#")
    func_header = "POWER"
    variable_headers = [RATE_NAME, PS_NAME, PD_NAME]

    compfunc = CompressorModelSampled3D(sampled_data=df, function_header=func_header)

    rates = np.asarray([10312429.5983791, 1816.34401461517])
    pss = np.asarray([68.04, 49.5160408])
    pds = np.asarray([111.90, 52.15884718])

    res = compfunc.evaluate(rate=rates, suction_pressure=pss, discharge_pressure=pds)
    expected = [6.61087753, 1.48375156]

    np.testing.assert_allclose(res, expected, rtol=1e-3)

    ps_pd = np.asarray([[68.04, 111.90], [49.5160, 59.4977]])

    convex_hull = ConvexHull(df[variable_headers][:].values)
    lower_rate_qh = get_lower_upper_qhull(convex_hull, axis=0)

    lower_convex_hull_0 = lower_rate_qh[0]
    lower_rate_points = lower_convex_hull_0.points
    lower_simplices = lower_convex_hull_0.simplices
    lower_equations = lower_convex_hull_0.equations

    lower_rate_qh = HalfConvexHull(
        points=lower_rate_points,
        simplices=lower_simplices,
        axis=0,
        equations=lower_equations,
    )
    min_rate_function = LinearInterpolatorSimplicesDefined(lower_rate_qh)
    res = min_rate_function(ps_pd)
    np.testing.assert_allclose(res, np.asarray([1e6, 2569600]))

    rates = np.asarray([4176211.71840906, 4208523.38473512, 10157353.220103897, 11.7399466])
    pss = np.asarray([68.195, 67.78, 48.04785538, 49.87203979])
    pds = np.asarray([74.66, 75.11, 89.07967377, 49.81638718])

    max_rates = compfunc.get_max_rate(ps=pss, pd=pds)
    np.testing.assert_allclose(max_rates, [15000000.0, 15000000.0, 13340853.0, 12243645.0])
    res = compfunc.evaluate(rate=rates, suction_pressure=pss, discharge_pressure=pds)
    np.testing.assert_allclose(res, [1.08134732, 1.10363911, 9.29246955, 1.46921105], rtol=1e-3)
