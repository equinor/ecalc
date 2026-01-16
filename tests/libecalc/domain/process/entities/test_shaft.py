"""Tests for Shaft domain entity."""

import pytest

from libecalc.domain.process.entities.shaft import SingleSpeedShaft, VariableSpeedShaft


class TestShaftMechanicalEfficiency:
    """Test mechanical efficiency behavior on shaft classes."""

    def test_default_mechanical_efficiency(self):
        """Shaft with no explicit efficiency should have η = 1.0."""
        shaft = VariableSpeedShaft()
        assert shaft.mechanical_efficiency == 1.0

    def test_custom_mechanical_efficiency(self):
        """Shaft can be created with custom mechanical efficiency."""
        shaft = VariableSpeedShaft(mechanical_efficiency=0.95)
        assert shaft.mechanical_efficiency == 0.95

    def test_single_speed_shaft_mechanical_efficiency(self):
        """SingleSpeedShaft supports mechanical efficiency."""
        shaft = SingleSpeedShaft(speed_rpm=3600.0, mechanical_efficiency=0.92)
        assert shaft.mechanical_efficiency == 0.92
        assert shaft.get_speed() == 3600.0

    def test_variable_speed_shaft_mechanical_efficiency(self):
        """VariableSpeedShaft supports mechanical efficiency."""
        shaft = VariableSpeedShaft(mechanical_efficiency=0.88)
        assert shaft.mechanical_efficiency == 0.88

    def test_mechanical_efficiency_boundary_valid(self):
        """Mechanical efficiency at boundary value 1.0 is valid."""
        shaft = VariableSpeedShaft(mechanical_efficiency=1.0)
        assert shaft.mechanical_efficiency == 1.0

    def test_mechanical_efficiency_near_zero_valid(self):
        """Very low mechanical efficiency is valid (though unlikely in practice)."""
        shaft = VariableSpeedShaft(mechanical_efficiency=0.01)
        assert shaft.mechanical_efficiency == 0.01

    @pytest.mark.parametrize(
        "efficiency",
        [0.0, -0.5, 1.1],
        ids=["zero", "negative", "above_one"],
    )
    def test_mechanical_efficiency_invalid_values(self, efficiency):
        """Invalid mechanical efficiency values should raise error."""
        with pytest.raises(ValueError, match="Mechanical efficiency must be in the range"):
            VariableSpeedShaft(mechanical_efficiency=efficiency)


class TestShaftSpeedBehavior:
    """Test that speed-related behavior still works with mechanical efficiency."""

    def test_variable_speed_shaft_set_speed(self):
        """Variable speed shaft can set and get speed."""
        shaft = VariableSpeedShaft(mechanical_efficiency=0.95)
        shaft.set_speed(5000.0)
        assert shaft.get_speed() == 5000.0

    def test_single_speed_shaft_fixed_speed(self):
        """Single speed shaft has fixed speed."""
        shaft = SingleSpeedShaft(speed_rpm=3600.0, mechanical_efficiency=0.92)
        assert shaft.get_speed() == 3600.0

    def test_single_speed_shaft_set_speed_raises(self):
        """Setting speed on single speed shaft should raise AttributeError."""
        shaft = SingleSpeedShaft(speed_rpm=3600.0, mechanical_efficiency=0.92)
        with pytest.raises(AttributeError, match="Cannot modify speed"):
            shaft.set_speed(5000.0)
