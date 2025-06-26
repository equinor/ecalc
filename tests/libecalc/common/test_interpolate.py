import numpy as np

from libecalc.common.interpolation import setup_interpolator


class TestInterpolate:
    def test_1d_interpolator_basic(self):
        """Test 1D interpolation returns correct value for in-bounds input."""
        x = np.array([0, 1, 2, 3])
        y = np.array([0, 10, 20, 30])
        interp = setup_interpolator([x], y)
        assert np.isclose(interp(1.5), 15)

    def test_1d_interpolator_out_of_bounds(self):
        """Test 1D interpolation returns fill_value for out-of-bounds input."""
        x = np.array([0, 1, 2])
        y = np.array([0, 1, 4])
        interp = setup_interpolator([x], y, fill_value=-1)
        assert interp(-1) == -1
        assert interp(3) == -1

    def test_nd_interpolator_basic(self):
        """Test N-dimensional interpolation returns correct value for in-bounds input."""
        x = np.array([0, 1, 0, 1])
        y = np.array([0, 0, 1, 1])
        z = np.array([0, 1, 2, 3])
        interp = setup_interpolator([x, y], z)
        assert np.isclose(interp([0.5, 0.5]), 1.5)

    def test_nd_interpolator_out_of_bounds(self):
        """Test N-dimensional interpolation returns fill_value for out-of-bounds input."""
        x = np.array([0, 1, 0, 1])
        y = np.array([0, 0, 1, 1])
        z = np.array([0, 1, 2, 3])
        interp = setup_interpolator([x, y], z, fill_value=-99)
        assert interp([2, 2]) == -99

    def test_1d_interpolator_single_point(self):
        """Test 1D interpolation with a single data point."""
        x = np.array([0])
        y = np.array([42])
        interp = setup_interpolator([x], y, fill_value=0)
        assert interp(0) == 42
        assert interp(1) == 0
