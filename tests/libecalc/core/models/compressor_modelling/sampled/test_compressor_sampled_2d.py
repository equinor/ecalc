import numpy as np
import pandas as pd

from libecalc.domain.process.compressor.core.sampled.compressor_model_sampled_2d import (
    CompressorModelSampled2DPsPd,
    CompressorModelSampled2DRatePd,
    CompressorModelSampled2DRatePs,
)
from libecalc.domain.process.compressor.core.sampled.constants import (
    PD_NAME,
    PS_NAME,
    RATE_NAME,
)


def test_rate_pd():
    data = pd.DataFrame(
        [
            [8, 5, 5],
            [3, 1, 5],
            [1, 4, 5],
            [2, 2, 5],
            [2, 6, 5],
            [3, 7, 5],
            [4, 8, 5],
            [7, 6, 5],
            [7, 3, 5],
            [5, 2, 5],
            [4, 4, 1],
        ],
        columns=[RATE_NAME, PD_NAME, "FUEL"],
    )

    convex_hull_2d_rate_pd_function = CompressorModelSampled2DRatePd(data, "FUEL")

    rate = np.asarray([4, 2.5, 5, 2, 1, 6, 7, 2, 2, 9, 9])
    pr_d = np.asarray([4, 4, 9, 7, 2, 1, 7, 10, 0, 1, 9])

    # PROJECT
    rate_expected = np.asarray([4, 2.5, 5, 3, 2, 6, 7, 4, 3, 9, 9])
    pd_expected = np.asarray([4, 4, 9, 7, 2, 2.5, 7, 10, 1, 5, 9])
    rate_proj, pd_proj = convex_hull_2d_rate_pd_function._project_variables_for_evaluation(
        rate=rate, discharge_pressure=pr_d
    )
    np.testing.assert_allclose(rate_proj, rate_expected)
    np.testing.assert_allclose(pd_proj, pd_expected)

    # EVALUATE
    expected_result = np.asarray([1, 3, np.nan, 5, 5, 5, np.nan, np.nan, 5, np.nan, np.nan])
    result = convex_hull_2d_rate_pd_function.evaluate(rate=rate, discharge_pressure=pr_d)
    np.testing.assert_allclose(result, expected_result)

    # MAX RATE
    expected_max_rate = np.asarray([8, 8, 8, 7, 4, 0])
    max_rate = convex_hull_2d_rate_pd_function.get_max_rate(discharge_pressure=np.asarray([0, 2, 4, 6, 8, 9]))
    np.testing.assert_allclose(max_rate, expected_max_rate)


def test_rate_ps():
    """Testing projection."""
    df_rate_ps = pd.DataFrame(
        [
            [3, 1, 5],
            [1, 4, 5],
            [2, 2, 5],
            [2, 6, 5],
            [3, 7, 5],
            [4, 8, 5],
            [7, 6, 5],
            [8, 5, 5],
            [7, 3, 5],
            [5, 2, 5],
            [4, 4, 1],
        ],
        columns=[RATE_NAME, PS_NAME, "FUEL"],
    )

    convex_hull_2d_rate_ps_function = CompressorModelSampled2DRatePs(df_rate_ps, "FUEL")

    rate = np.asarray([4, 2.5, 5.5, 9, 6, 0, 1, 0, 1])
    pr_s = np.asarray([4, 4, 9, 4, 2, 0, 1.5, 6, 9])

    rate_expected = np.asarray([4, 2.5, 5.5, 9, 6, 3, 2.5, 2, 4])
    ps_expected = np.asarray([4, 4, 7, 4, 2, 0, 1.5, 6, 8])
    rate_proj, ps_proj = convex_hull_2d_rate_ps_function._project_variables_for_evaluation(rate=rate, ps=pr_s)
    np.testing.assert_allclose(rate_proj, rate_expected)
    np.testing.assert_allclose(ps_proj, ps_expected)

    expected_result = np.asarray([1, 3, 5, np.nan, np.nan, np.nan, 5, 5, 5])
    result = convex_hull_2d_rate_ps_function.evaluate(rate=rate, suction_pressure=pr_s)
    np.testing.assert_allclose(result, expected_result)

    # Testing max rate function
    expected_max_rate = np.asarray([0, 5, 7.5, 8, 8])
    max_rate = convex_hull_2d_rate_ps_function.get_max_rate(np.asarray([0, 2, 4, 6, 9]))
    np.testing.assert_allclose(max_rate, expected_max_rate)


def test_ps_pd():
    """Testing projection."""
    df_ps_pd = pd.DataFrame(
        [
            [1, 3, 5],
            [2, 2, 5],
            [4, 1, 5],
            [6, 2, 5],
            [7, 3, 5],
            [8, 4, 5],
            [6, 7, 5],
            [5, 8, 5],
            [3, 7, 5],
            [2, 5, 5],
            [4, 4, 1],
        ],
        columns=[PS_NAME, PD_NAME, "FUEL"],
    )

    convex_hull_2d_ps_pd_function = CompressorModelSampled2DPsPd(df_ps_pd, "FUEL")

    pr_s = np.asarray([4, 5, 9, 6, 0, 1, 0, 1, 4, 9, 9])
    pr_d = np.asarray([4, 9, 4, 2, 0, 1.5, 6, 9, 2.5, 2, 5])

    ps_expected = np.asarray([4, 5, 8, 6, 0, 1, 0, 1, 4, 8, 22 / 3])
    pd_expected = np.asarray([4, 9, 4, 2, 3, 3, 6, 9, 2.5, 4, 5])
    ps_proj, pd_proj = convex_hull_2d_ps_pd_function._project_variables_for_evaluation(ps=pr_s, pd=pr_d)
    np.testing.assert_allclose(ps_proj, ps_expected)
    np.testing.assert_allclose(pd_proj, pd_expected)

    expected_result = np.asarray([1, np.nan, 5, 5, np.nan, 5, np.nan, np.nan, 3, 5, 5])
    result = convex_hull_2d_ps_pd_function.evaluate(suction_pressure=pr_s, discharge_pressure=pr_d)
    np.testing.assert_allclose(result, expected_result)
