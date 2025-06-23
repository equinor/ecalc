import pytest

from libecalc.domain.process.value_objects.fluid_stream.conditions import ProcessConditions


class TestProcessConditions:
    """Test suite for the ProcessConditions class."""

    def test_init_and_properties(self):
        """Test initialization and basic property conversions."""
        conditions = ProcessConditions(temperature_kelvin=300.0, pressure_bara=10.0)

        # Test direct attributes
        assert conditions.temperature_kelvin == 300.0
        assert conditions.pressure_bara == 10.0

        # Test one conversion property
        assert conditions.temperature_celsius == pytest.approx(26.85)

    def test_standard_conditions(self):
        """Test the standard_conditions factory method."""
        conditions = ProcessConditions.standard_conditions()

        # Standard conditions should be 15°C (288.15K) and 1.01325 bara
        assert conditions.temperature_kelvin == pytest.approx(288.15)
        assert conditions.pressure_bara == pytest.approx(1.01325)
