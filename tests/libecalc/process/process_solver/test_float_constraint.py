import pytest

from libecalc.process.process_solver.float_constraint import AbsoluteTolerance, FloatConstraint, RelativeTolerance


class TestFloatConstraint:
    def test_default_uses_relative_tolerance(self):
        constraint = FloatConstraint(100.0)
        assert constraint == 100.0 * (1 + 1e-4)
        assert constraint != 100.0 * (1 + 1e-1)

    def test_relative_tolerance(self):
        constraint = FloatConstraint(200.0, RelativeTolerance(0.01))
        assert constraint == 202.0
        assert constraint != 203.0

    def test_absolute_tolerance(self):
        constraint = FloatConstraint(200.0, AbsoluteTolerance(0.5))
        assert constraint == 200.4
        assert constraint != 201.0

    @pytest.mark.parametrize("tolerance", [RelativeTolerance, AbsoluteTolerance])
    @pytest.mark.parametrize("value", [-1e-3, float("nan"), float("inf")])
    def test_invalid_tolerance_raises(self, tolerance, value):
        with pytest.raises(ValueError, match="finite and non-negative"):
            tolerance(value)

    def test_with_value_keeps_tolerance(self):
        tolerance = AbsoluteTolerance(0.5)
        constraint = FloatConstraint(10, tolerance).with_value(20)
        assert constraint.value == 20
        assert constraint.tolerance == tolerance
