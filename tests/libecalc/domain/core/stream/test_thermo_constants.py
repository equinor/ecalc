from libecalc.domain.process.core.stream.thermo_constants import ThermodynamicConstants


class TestThermodynamicConstants:
    """Minimal test suite for ThermodynamicConstants."""

    def test_validate_components(self):
        """Test that component validation runs without errors.

        This test simply verifies that the component definitions are structurally valid.
        """
        # Should run without raising exceptions
        ThermodynamicConstants.validate_components()

        # If we reach here, the validation passed
        assert True
