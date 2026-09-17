import numpy as np
import pytest
from scipy.spatial import ConvexHull

from libecalc.domain.process.compressor.core.sampled.convex_hull_common import (
    LinearInterpolatorSimplicesDefined as LegacyLinearInterpolatorSimplicesDefined,
)
from libecalc.domain.process.compressor.core.sampled.convex_hull_common import (
    get_lower_upper_qhull as legacy_get_lower_upper_qhull,
)
from libecalc.domain.process.compressor.core.sampled.convex_hull_common import (
    sort_ndarray_by_column as legacy_sort_ndarray_by_column,
)
from libecalc.energy.models.convex_hull import (
    HalfConvexHull,
    LinearSurfaceInterpolator,
    get_lower_upper_qhull,
    sort_ndarray_by_column,
)


def _assert_half_hull_equal(actual: HalfConvexHull, expected) -> None:
    np.testing.assert_array_equal(actual.points, expected.points)
    np.testing.assert_array_equal(actual.simplices, expected.simplices)
    np.testing.assert_allclose(actual.equations, expected.equations, rtol=1e-12, atol=1e-12)
    np.testing.assert_array_equal(actual.original_indices, expected.original_qhull_indices)


def _structured_points_2d(rng: np.random.Generator, rate_count: int, pressure_count: int) -> np.ndarray:
    """A rate x pressure grid resembling a real sampled compressor table, so that the
    convex hull always has a well-defined "upper monotonic" boundary (unlike an
    arbitrary point cloud, where that selection can be empty).
    """
    rates = np.linspace(1e6, 1e6 * (1 + rate_count), rate_count)
    pressures = np.linspace(40.0, 40.0 + 10 * pressure_count, pressure_count)
    points = np.array([[rate, pressure] for rate in rates for pressure in pressures], dtype=np.float64)
    return points + rng.normal(scale=1e-3, size=points.shape)


def _structured_points_3d(rng: np.random.Generator, rate_count: int, pressure_count: int) -> np.ndarray:
    rates = np.linspace(1e6, 1e6 * (1 + rate_count), rate_count)
    suction_pressures = np.linspace(40.0, 40.0 + 10 * pressure_count, pressure_count)
    discharge_pressures = np.linspace(100.0, 100.0 + 20 * pressure_count, pressure_count)
    points = np.array(
        [[rate, ps, pd] for rate in rates for ps in suction_pressures for pd in discharge_pressures],
        dtype=np.float64,
    )
    return points + rng.normal(scale=1e-3, size=points.shape)


def test_sort_ndarray_by_column_matches_legacy() -> None:
    rng = np.random.default_rng(0)
    array = rng.uniform(-10, 10, size=(20, 3))
    for column_index in range(3):
        np.testing.assert_array_equal(
            sort_ndarray_by_column(array, column_index),
            legacy_sort_ndarray_by_column(array, column_index),
        )


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
def test_get_lower_upper_qhull_matches_legacy_3d(seed: int) -> None:
    rng = np.random.default_rng(seed)
    points = _structured_points_3d(rng, rate_count=4, pressure_count=4)
    convex_hull = ConvexHull(points)

    lower, upper, monotonic = get_lower_upper_qhull(convex_hull, axis=0)
    legacy_lower, legacy_upper, legacy_monotonic = legacy_get_lower_upper_qhull(convex_hull, axis=0)

    _assert_half_hull_equal(lower, legacy_lower)
    _assert_half_hull_equal(upper, legacy_upper)
    assert (monotonic is None) == (legacy_monotonic is None)
    if monotonic is not None:
        assert legacy_monotonic is not None
        _assert_half_hull_equal(monotonic, legacy_monotonic)


@pytest.mark.parametrize("case_2d", ["rate_ps", "rate_pd"])
@pytest.mark.parametrize("seed", [0, 1, 2])
def test_get_lower_upper_qhull_matches_legacy_2d(seed: int, case_2d: str) -> None:
    rng = np.random.default_rng(seed)
    points = _structured_points_2d(rng, rate_count=5, pressure_count=5)
    convex_hull = ConvexHull(points)

    lower, upper, monotonic = get_lower_upper_qhull(convex_hull, axis=0, case_2d=case_2d)
    legacy_lower, legacy_upper, legacy_monotonic = legacy_get_lower_upper_qhull(convex_hull, axis=0, case_2d=case_2d)

    _assert_half_hull_equal(lower, legacy_lower)
    _assert_half_hull_equal(upper, legacy_upper)
    assert (monotonic is None) == (legacy_monotonic is None)
    if monotonic is not None:
        assert legacy_monotonic is not None
        _assert_half_hull_equal(monotonic, legacy_monotonic)


@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
@pytest.mark.parametrize("fill_value", [np.nan, 0.0, np.inf])
@pytest.mark.parametrize("half_hull_kind", ["lower", "upper", "monotonic"])
def test_linear_surface_interpolator_matches_legacy(seed: int, fill_value: float, half_hull_kind: str) -> None:
    rng = np.random.default_rng(seed)
    points = _structured_points_3d(rng, rate_count=4, pressure_count=4)
    convex_hull = ConvexHull(points)
    lower, upper, monotonic = get_lower_upper_qhull(convex_hull, axis=0)
    legacy_lower, legacy_upper, legacy_monotonic = legacy_get_lower_upper_qhull(convex_hull, axis=0)
    half_hull = {"lower": lower, "upper": upper, "monotonic": monotonic}[half_hull_kind]
    legacy_half_hull = {"lower": legacy_lower, "upper": legacy_upper, "monotonic": legacy_monotonic}[half_hull_kind]
    if half_hull is None or half_hull.points.shape[0] < 3:
        pytest.skip("No (non-degenerate) half hull of this kind for this seed.")

    interpolator = LinearSurfaceInterpolator(half_hull, fill_value=fill_value)
    legacy_interpolator = LegacyLinearInterpolatorSimplicesDefined(legacy_half_hull, fill_value=fill_value)

    query = np.stack(
        [
            rng.uniform(40.0, 40.0 + 10 * 4, size=200),
            rng.uniform(100.0, 100.0 + 20 * 4, size=200),
        ],
        axis=-1,
    )
    np.testing.assert_allclose(
        interpolator.evaluate(query),
        legacy_interpolator.evaluate(variable_array=query),
        rtol=1e-9,
        atol=1e-9,
        equal_nan=True,
    )


def test_get_lower_upper_qhull_2d_unknown_case_returns_none() -> None:
    rng = np.random.default_rng(0)
    points = _structured_points_2d(rng, rate_count=5, pressure_count=5)
    convex_hull = ConvexHull(points)

    _, _, monotonic = get_lower_upper_qhull(convex_hull, axis=0, case_2d="ps_pd")
    _, _, legacy_monotonic = legacy_get_lower_upper_qhull(convex_hull, axis=0, case_2d="ps_pd")

    assert monotonic is None
    assert legacy_monotonic is None


def test_get_lower_upper_qhull_axis_nonzero_matches_legacy() -> None:
    rng = np.random.default_rng(0)
    points = _structured_points_3d(rng, rate_count=4, pressure_count=4)
    convex_hull = ConvexHull(points)

    for axis in (1, 2):
        lower, upper, monotonic = get_lower_upper_qhull(convex_hull, axis=axis)
        legacy_lower, legacy_upper, legacy_monotonic = legacy_get_lower_upper_qhull(convex_hull, axis=axis)

        _assert_half_hull_equal(lower, legacy_lower)
        _assert_half_hull_equal(upper, legacy_upper)
        # "upper monotonic" is only ever defined for axis 0 (matching legacy).
        assert monotonic is None
        assert legacy_monotonic is None


def test_get_lower_upper_qhull_empty_monotonic_hull_matches_legacy() -> None:
    # A random (non-structured) point cloud is unlikely to have any facet satisfying the
    # monotonicity condition, so the "upper monotonic" half hull is applicable (not None)
    # but empty on both sides - this was the exact case get_lower_upper_qhull previously
    # got wrong (collapsing empty to None instead of matching legacy's applicable-but-empty
    # HalfConvexHull).
    rng = np.random.default_rng(24)
    points = rng.uniform(0.0, 1.0, size=(10, 3))
    convex_hull = ConvexHull(points)

    _, _, monotonic = get_lower_upper_qhull(convex_hull, axis=0)
    _, _, legacy_monotonic = legacy_get_lower_upper_qhull(convex_hull, axis=0)

    assert monotonic is not None
    assert legacy_monotonic is not None
    assert monotonic.points.shape[0] == 0
    assert legacy_monotonic.points.shape[0] == 0
    _assert_half_hull_equal(monotonic, legacy_monotonic)


def test_linear_surface_interpolator_evaluate_rejects_wrong_column_count() -> None:
    rng = np.random.default_rng(0)
    points = _structured_points_3d(rng, rate_count=4, pressure_count=4)
    convex_hull = ConvexHull(points)
    lower, _, _ = get_lower_upper_qhull(convex_hull, axis=0)
    interpolator = LinearSurfaceInterpolator(lower)

    with pytest.raises(ValueError, match="Expected 2 columns"):
        interpolator.evaluate(np.zeros((5, 3)))


def test_linear_surface_interpolator_falls_back_outside_every_simplex() -> None:
    # A query point far outside the sampled envelope's variable-axis range falls
    # outside every simplex of the half hull, exercising the LinearNDInterpolator
    # fallback path (matching legacy's own out-of-simplex fallback behaviour).
    rng = np.random.default_rng(0)
    points = _structured_points_3d(rng, rate_count=4, pressure_count=4)
    convex_hull = ConvexHull(points)
    lower, _, _ = get_lower_upper_qhull(convex_hull, axis=0)
    legacy_lower, _, _ = legacy_get_lower_upper_qhull(convex_hull, axis=0)
    interpolator = LinearSurfaceInterpolator(lower, fill_value=np.nan)
    legacy_interpolator = LegacyLinearInterpolatorSimplicesDefined(legacy_lower, fill_value=np.nan)

    far_outside = np.array([[1e9, 1e9]])
    np.testing.assert_allclose(
        interpolator.evaluate(far_outside),
        legacy_interpolator.evaluate(variable_array=far_outside),
        equal_nan=True,
    )
