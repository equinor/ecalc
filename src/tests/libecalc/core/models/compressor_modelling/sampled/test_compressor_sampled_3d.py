from pathlib import Path

import numpy as np
import pandas as pd
from libecalc.core.models.compressor.sampled.compressor_model_sampled_3d import (
    EPSILON,
    CompressorModelSampled3D,
    _project_on_pd,
    _project_on_ps,
    _project_on_rate,
    _setup_maximum_ps_projection_functions,
    _setup_minimum_pd_projection_functions,
    _setup_minimum_rate_projection_functions,
)
from libecalc.core.models.compressor.sampled.constants import (
    PD_NAME,
    PS_NAME,
    RATE_NAME,
)
from libecalc.core.models.compressor.sampled.convex_hull_common import HalfConvexHull


def test_CompressorSampled3D():
    data = pd.DataFrame(
        [
            [1000000, 50, 162, 52765],
            [1000000, 50, 258, 76928],
            [1000000, 50, 394, 118032],
            [1000000, 50, 471, 145965],
            [3000000, 50, 237, 71918],
            [3000000, 50, 258, 109823],
            [3000000, 50, 449, 137651],
            [7000000, 50, 322, 139839],
            [1000000, 51, 166, 53000],
            [1000000, 51, 480, 148000],
            [1000000, 52, 171, 54441],
            [1000000, 52, 215, 65205],
            [1000000, 52, 336, 98692],
            [1000000, 52, 487, 151316],
            [3000000, 52, 249, 74603],
            [3000000, 52, 384, 114277],
            [3000000, 52, 466, 143135],
            [7200000, 52, 362, 144574],
        ],
        columns=[RATE_NAME, PS_NAME, PD_NAME, "FUEL"],
    )

    func_header = "FUEL"
    # func_3d = CompressorPumpTabular(df_3d, variables, func_header)
    func_3d = CompressorModelSampled3D(data, func_header)

    # Max rates
    # ps = 50
    result = func_3d.get_max_rate(
        ps=50 * np.ones(10), pd=np.array([100, 162, 163, 322, 340, 362, 385.5, 400, 449, 487])
    )

    expected = [
        7e6,
        7e6,
        7e6,
        7e6,
        6433070.86,
        5740157.48,
        5e6,
        4543307.09,
        3e6,
        0,
    ]
    np.testing.assert_allclose(result, expected)

    result = func_3d.get_max_rate(ps=52 * np.ones(8), pd=np.array([100, 162, 171, 362, 414, 476.5, 487, 488]))
    np.testing.assert_allclose(result, [7.2e6, 7.2e6, 7.2e6, 7.2e6, 5.1e6, 2e6, 1e6, 0])

    result = func_3d.get_max_rate(ps=51 * np.ones(9), pd=np.array([100, 162, 166, 166.5, 323, 342, 411, 480, 488]))
    np.testing.assert_allclose(
        result,
        [7.1e6, 7.1e6, 7.1e6, 7.1e6, 7.1e6, 7.1e6, 4.87788461e6, 1e6, 0],
    )

    # ps = 50.5
    result = func_3d.get_max_rate(ps=50.5 * np.ones(2), pd=np.array([100, 332]))
    np.testing.assert_allclose(result, [7.05e6, 7.05e6])

    # Selected upper rate points
    result = func_3d.get_max_rate(
        ps=np.array([50, 50, 50, 51, 52, 52, 52]), pd=np.array([471, 449, 322, 480, 487, 466, 362])
    )
    np.testing.assert_allclose(result, [1e6, 3e6, 7e6, 1e6, 1e6, 3e6, 7.2e6])

    # Projection and evaluation
    rate = np.asarray([1, 1, 1, 1, 1, 7.1e6, 4e6])
    pr_s = np.asarray([51, 50.5, 53, 49, 51, 51, 50])
    pr_d = np.asarray([300, 100, 250, 300, 550, 300, 200])
    rate_proj, ps_proj, pd_proj = func_3d._project_variables_for_evaluation(
        rate / func_3d._scale_factor_rate, pr_s, pr_d
    )
    rate_proj = rate_proj * func_3d._scale_factor_rate

    expected_rate = [1e6, 1e6, 1e6, 1e6, 1e6, 7.1e6, 4e6]
    expected_ps = [51, 50.5, 52, 49, 51, 51, 50]
    expected_pd = [300, 164, 250, 300, 550, 342, 242]
    np.testing.assert_allclose(rate_proj, expected_rate)
    np.testing.assert_allclose(ps_proj, expected_ps)
    np.testing.assert_allclose(pd_proj, expected_pd)

    result = func_3d.evaluate(rate=rate, suction_pressure=pr_s, discharge_pressure=pr_d)
    res_min_max_rate_projected = func_3d._project_and_calculate_outsiders_rate(
        rate=rate / func_3d._scale_factor_rate, suction_pressure=pr_s, discharge_pressure=pr_d
    )
    np.testing.assert_allclose(result[:-1], res_min_max_rate_projected[:-1])
    res_min_pd_projected = func_3d._project_and_calculate_outsiders_pd(
        rate=rate / func_3d._scale_factor_rate, suction_pressure=pr_s, discharge_pressure=pr_d
    )
    np.testing.assert_allclose(result[-1], res_min_pd_projected[-1])

    rate = np.asarray([1e6, 1e6, 1e6, 1e6, 1e6, 2e6])
    pr_s = np.asarray([50, 52, 53, 50, 50.5, 50])
    pr_d = np.asarray([162, 150, 150, 432.5, 162, 162])

    rate_proj, ps_proj, pd_proj = func_3d._project_variables_for_evaluation(
        rate / func_3d._scale_factor_rate, pr_s, pr_d
    )
    rate_proj = rate_proj * func_3d._scale_factor_rate
    np.testing.assert_allclose(
        rate_proj,
        [1000000.0, 1000000.0, 1000000.0, 1000000.0, 1000000.0, 2000000.0],
    )
    np.testing.assert_allclose(ps_proj, [50, 52, 52, 50, 50.5, 50])
    np.testing.assert_allclose(pd_proj, [162, 171, 171, 432.5, 164, 188.66666667])

    result = func_3d.evaluate(rate=rate, suction_pressure=pr_s, discharge_pressure=pr_d)
    np.testing.assert_allclose(result, [52765, 54441, 54441, 131998.5, 52882.5, 67277.3333333333])


def test_CompressorSampled3D_cube():
    data = pd.DataFrame(
        [
            [1, 1, 1, 5],
            [3, 1, 1, 5],
            [1, 3, 1, 5],
            [3, 3, 1, 5],
            [1, 1, 3, 5],
            [3, 1, 3, 5],
            [1, 3, 3, 5],
            [3, 3, 3, 5],
        ],
        columns=[RATE_NAME, PS_NAME, PD_NAME, "FUEL"],
    )

    func_header = "FUEL"

    cube_QHT3D = CompressorModelSampled3D(data, func_header)

    rate = np.asarray([2, 0, 2, 2, 4, 2, 2, 0])
    pr_s = np.asarray([2, 2, 4, 2, 2, 0, 2, 4])
    pr_d = np.asarray([2, 2, 2, 0, 2, 2, 4, 0])

    rate_proj, ps_proj, pd_proj = cube_QHT3D._project_variables_for_evaluation(
        rate / cube_QHT3D._scale_factor_rate, pr_s, pr_d
    )
    rate_proj = rate_proj * cube_QHT3D._scale_factor_rate
    expected_rate = [2, 1, 2, 2, 4, 2, 2, 1]
    expected_ps = [2, 2, 3, 2, 2, 0, 2, 3]
    expected_pd = [2, 2, 2, 1, 2, 2, 4, 1]
    np.testing.assert_allclose(rate_proj, expected_rate)
    np.testing.assert_allclose(ps_proj, expected_ps)
    np.testing.assert_allclose(pd_proj, expected_pd)

    result = cube_QHT3D.evaluate(rate, pr_s, pr_d)

    expected = [5, 5, 5, 5, np.nan, np.nan, np.nan, 5]
    np.testing.assert_allclose(result, expected)

    res_min_max_rate_projected = cube_QHT3D._project_and_calculate_outsiders_rate(
        rate=rate / cube_QHT3D._scale_factor_rate, suction_pressure=pr_s, discharge_pressure=pr_d
    )
    np.testing.assert_allclose(result[[1, -1]], res_min_max_rate_projected[[1, -1]])

    res_min_pd_projected = cube_QHT3D._project_and_calculate_outsiders_pd(
        rate=rate / cube_QHT3D._scale_factor_rate, suction_pressure=pr_s, discharge_pressure=pr_d
    )
    np.testing.assert_allclose(result[[3, -1]], res_min_pd_projected[[3, -1]])

    res_max_ps_projected = cube_QHT3D._project_and_calculate_outsiders_ps(
        rate=rate / cube_QHT3D._scale_factor_rate, suction_pressure=pr_s, discharge_pressure=pr_d
    )
    np.testing.assert_allclose(result[[2, -1]], res_max_ps_projected[[2, -1]])


def test_CompressorSampled3D_non_monotonic_rate():
    # Test max rate outside monotonic is projected correctly
    df = pd.DataFrame(
        [
            [1, 1, 1, 1],
            [4, 1, 4, 16],
            [3, 1, 5, 10],
            [1, 1, 6, 6],
            [1, 2, 1, 1],
            [4, 2, 4, 10],
            [3, 2, 5, 10],
            [1, 2, 6, 6],
        ],
        columns=[RATE_NAME, PS_NAME, PD_NAME, "FUEL"],
    )

    func_header = "FUEL"

    qh = CompressorModelSampled3D(df, func_header)

    max_rate = qh.get_max_rate(ps=1, pd=2)[0]
    np.testing.assert_allclose(max_rate, 4)

    rate = np.asarray([max_rate])
    pr_s = np.asarray([1.0])
    pr_d = np.asarray([2.0])

    rate_proj, ps_proj, pd_proj = qh._project_variables_for_evaluation(rate / qh._scale_factor_rate, pr_s, pr_d)
    rate_proj = rate_proj * qh._scale_factor_rate
    np.testing.assert_allclose(rate_proj, [4])
    np.testing.assert_allclose(ps_proj, [1])
    np.testing.assert_allclose(pd_proj, [4])

    # Test max rate outside monotonic on a large real input
    testfile = Path(__file__).parent / "input" / "compressor_sampled_3d_vsd_testdata.csv"
    df = pd.read_csv(testfile, comment="#")
    qh = CompressorModelSampled3D(df, func_header)
    max_rate = qh.get_max_rate(ps=np.array([40]), pd=np.array([50]))
    np.testing.assert_allclose(max_rate, 8e6)

    rate = np.asarray(max_rate)
    pr_s = np.asarray([40])
    pr_d = np.asarray([50])

    rate_proj, ps_proj, pd_proj = qh._project_variables_for_evaluation(rate / qh._scale_factor_rate, pr_s, pr_d)
    rate_proj *= qh._scale_factor_rate
    np.testing.assert_allclose(rate_proj, max_rate)
    np.testing.assert_allclose(ps_proj, [40])
    np.testing.assert_allclose(pd_proj, [107.34])

    result = qh.evaluate(rate, pr_s, pr_d)
    np.testing.assert_allclose(result, 114516.92)


def test_projection_functions():
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

    (
        min_rate_max_ps_1d_func,
        min_rate_min_pd_1d_func,
        min_rate_2d_func,
    ) = _setup_minimum_rate_projection_functions(lower_rate_qh, rate_axis=0, ps_axis=1, pd_axis=2)

    # Test rate projection functions
    res = min_rate_max_ps_1d_func([0, 1, 1.5, 2, 3.5, 6, 7, 10])
    expected = [3, 3, 4.5, 6, 6.5, 6, 5, 5]
    np.testing.assert_allclose(res, expected)

    res = min_rate_min_pd_1d_func([0, 1, 2, 3, 4.5, 6, 6.5, 7, 100])
    expected = [3, 3, 2, 1, 1.5, 2, 3.5, 5, 5]
    np.testing.assert_allclose(res, expected)

    res = min_rate_2d_func(np.asarray([[3, 1], [2.5, 3.5], [2.75, 2.25], [2, 1], [9, 5]]))
    expected = [4, 2.5, 3.25, 0, 0]
    np.testing.assert_allclose(res, expected)

    # Redo test, but with altered columns
    lower_rate_points_alt = lower_rate_points[:, [2, 0, 1]]
    lower_rate_equations_alt = lower_rate_equations[:, [2, 0, 1, 3]]
    lower_rate_alt_qh = HalfConvexHull(
        points=lower_rate_points_alt,
        simplices=lower_rate_simplices,
        equations=lower_rate_equations_alt,
        axis=1,
    )

    (
        min_rate_max_ps_1d_func_alt,
        min_rate_min_pd_1d_func_alt,
        min_rate_2d_func_alt,
    ) = _setup_minimum_rate_projection_functions(lower_rate_alt_qh, rate_axis=1, ps_axis=2, pd_axis=0)
    np.testing.assert_allclose(min_rate_min_pd_1d_func.x, min_rate_min_pd_1d_func_alt.x)
    np.testing.assert_allclose(min_rate_min_pd_1d_func.y, min_rate_min_pd_1d_func_alt.y)
    np.testing.assert_allclose(
        min_rate_min_pd_1d_func.fill_value,
        min_rate_min_pd_1d_func_alt.fill_value,
    )

    np.testing.assert_allclose(min_rate_max_ps_1d_func.x, min_rate_max_ps_1d_func_alt.x)
    np.testing.assert_allclose(min_rate_max_ps_1d_func.y, min_rate_max_ps_1d_func_alt.y)
    np.testing.assert_allclose(
        min_rate_max_ps_1d_func.fill_value,
        min_rate_max_ps_1d_func_alt.fill_value,
    )

    res_alt = min_rate_2d_func_alt(np.asarray([[3, 1], [2.5, 3.5], [2.75, 2.25], [2, 1], [9, 5]]))
    np.testing.assert_allclose(res, res_alt)

    # Test _project_on_rate
    res_rate, res_ps, res_pd = _project_on_rate(
        lower_rate_qh_lower_pd_function=min_rate_min_pd_1d_func,
        lower_rate_qh_upper_ps_function=min_rate_max_ps_1d_func,
        minimum_rate_function=min_rate_2d_func,
        rate=np.array([0, 0, 0, 1, 2, 1, 0]),
        suction_pressure=np.array([4, 6, 7, 7, 7, 3, 0.5]),
        discharge_pressure=np.array([4, 1, 3, 7, 6, 6.5, 2]),
    )
    expected_rate = np.array([3, 5, 4, 2, 3, 1, 0])
    expected_ps = np.array([4, 6, 7, 5, 6, 3, 0.5])
    expected_pd = np.array([4, 2, 5, 7, 6, 6.5, 3])
    np.testing.assert_allclose(res_rate, expected_rate, atol=EPSILON)
    np.testing.assert_allclose(res_ps, expected_ps, atol=EPSILON)
    np.testing.assert_allclose(res_pd, expected_pd, atol=EPSILON)

    # Test pd projection functions
    lower_pd_qh = lower_rate_qh.reorder_axes(axis=2, variable_axes=[1, 0])
    (
        min_pd_min_rate_1d_func,
        min_pd_max_ps_1d_func,
        min_pd_2d_func,
    ) = _setup_minimum_pd_projection_functions(lower_pd_qh, rate_axis=0, ps_axis=1, pd_axis=2)
    res = min_pd_min_rate_1d_func([0, 1, 2, 3, 4.5, 6, 6.5, 7, 100])
    expected = [3, 3, 2, 1, 1.5, 2, 3.5, 5, 5]
    np.testing.assert_allclose(res, expected)

    res = min_pd_max_ps_1d_func([0, 1, 1.5, 2, 3.5, 6, 7, 10])
    expected = [3, 3, 4.5, 6, 6.5, 6, 5, 5]
    np.testing.assert_allclose(res, expected)

    res = min_pd_2d_func(np.asarray([[1, 3], [3.5, 2.5], [2.25, 2.75], [1, 2], [5, 9]]))
    expected = [4, 2.5, 3.25, 0, 0]
    np.testing.assert_allclose(res, expected)

    # Test _project_on_pd
    res_rate, res_ps, res_pd = _project_on_pd(
        lower_pd_qh_lower_rate_function=min_pd_min_rate_1d_func,
        lower_pd_qh_upper_ps_function=min_pd_max_ps_1d_func,
        minimum_pd_function=min_pd_2d_func,
        discharge_pressure=np.array([0, 0, 0, 1, 2, 1, 0]),
        suction_pressure=np.array([4, 6, 7, 7, 7, 3, 0.5]),
        rate=np.array([4, 1, 3, 7, 6, 6.5, 2]),
    )
    expected_pd = np.array([3, 5, 4, 2, 3, 1, 0])
    expected_ps = np.array([4, 6, 7, 5, 6, 3, 0.5])
    expected_rate = np.array([4, 2, 5, 7, 6, 6.5, 3])
    np.testing.assert_allclose(res_rate, expected_rate, atol=EPSILON)
    np.testing.assert_allclose(res_ps, expected_ps, atol=EPSILON)
    np.testing.assert_allclose(res_pd, expected_pd, atol=EPSILON)

    # Test ps projection functions
    upper_ps_qh = lower_rate_qh
    (
        max_ps_min_rate_1d_func,
        max_ps_min_pd_1d_func,
        max_ps_2d_func,
    ) = _setup_maximum_ps_projection_functions(upper_ps_qh, rate_axis=0, ps_axis=1, pd_axis=2)
    res = max_ps_min_rate_1d_func(np.array([0, 1, 2, 5, 7, 100]))
    expected = np.array([4, 4, 3, 4.0 / 3, 2, 2])
    np.testing.assert_allclose(res, expected)

    res = max_ps_min_pd_1d_func(np.array([0, 1, 3, 4.5, 5, 10]))
    expected = np.array([6, 6, 2, 1.5, 2, 2])
    np.testing.assert_allclose(res, expected)

    res = max_ps_2d_func(np.asarray([[3, 4], [1.5, 4.5], [2.25, 4.25], [4, 6]]))
    expected = np.array([4, 1.5, 2.75, np.inf])
    np.testing.assert_allclose(res, expected)

    # Test _project_on_ps
    res_rate, res_ps, res_pd = _project_on_ps(
        upper_ps_qh_lower_rate_function=max_ps_min_rate_1d_func,
        upper_ps_qh_lower_pd_function=max_ps_min_pd_1d_func,
        maximum_ps_function=max_ps_2d_func,
        rate=np.array([3, 1, 2, 5, 1, 5, 5]),
        suction_pressure=np.array([5, 2, 2, 7, 6, 1, 100]),
        discharge_pressure=np.array([4, 3, 1, 1, 6.5, 6, 6]),
    )
    expected_rate = np.array([3, 2, 4, 5, 1.5, 5, 5])
    expected_ps = np.array([4, 1, 2, 6, 3.5, 1, 100])
    expected_pd = np.array([4, 3, 1, 2, 6.5, 6, 6])
    np.testing.assert_allclose(res_rate, expected_rate)
    np.testing.assert_allclose(res_ps, expected_ps)
    np.testing.assert_allclose(res_pd, expected_pd)


def test_injection_comp():
    inj_comp_data = Path(__file__).parent / "input" / "compressor_sampled_3d_vsd_testdata.csv"
    df = pd.read_csv(inj_comp_data, comment="#")
    func_header = "FUEL"
    compressor_function = CompressorModelSampled3D(df, func_header, rescale_rate=False)

    rate = np.asarray(
        [2730173.25, 2360662.5, 9251707, 9191994, 9079736, 9085830, 9076572, 9068991]
    )  # rates from 2 and onwards - system of two, two compressors, divide rate to complete test
    pss = 56 * np.ones(rate.size)
    pds = 420 * np.ones(rate.size)

    result = compressor_function.evaluate(rate=rate, suction_pressure=pss, discharge_pressure=pds)
    result_2_comps = 2 * compressor_function.evaluate(rate=rate / 2.0, suction_pressure=pss, discharge_pressure=pds)
    np.testing.assert_allclose(result[:2], [145184.0, 144075.0], rtol=1e-3)
    assert np.isnan(result[2:]).all()
    np.testing.assert_allclose(
        result_2_comps,
        [277157.0, 277157.0, 295125.0, 295008.0, 294788.0, 294800.0, 294782.0, 294767.0],
        rtol=1e-3,
    )


def test_compressor_sampled_3d():
    test_input_data = Path(__file__).parent / "input" / "compressor_sampled_3d_testdata3.csv"
    df = pd.read_csv(test_input_data, comment="#")
    func_header = "POWER"
    compressor_function = CompressorModelSampled3D(df, func_header, rescale_rate=False)
    rate = np.asarray([59.50651104])
    pss = np.asarray([140.0931049])
    pds = np.asarray([178.3903971])

    result = compressor_function.evaluate(rate=rate, suction_pressure=pss, discharge_pressure=pds)
    np.testing.assert_allclose(result, 3.80394719)

    rate = np.asarray([13.47349524])
    pss = np.asarray([130.8581215])
    pds = np.asarray([0])

    result = compressor_function.evaluate(rate=rate, suction_pressure=pss, discharge_pressure=pds)
    np.testing.assert_allclose(result, 3.92494047)
