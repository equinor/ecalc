from libecalc.domain.process.entities.fluid_stream.constants import ThermodynamicConstants
from libecalc.domain.process.entities.fluid_stream.utils import FluidComposition


def validate_components():
    """Validate that all components defined in FluidComposition have their properties defined."""
    fluid_composition_fields = set(FluidComposition.model_fields.keys())
    missing_components = fluid_composition_fields - ThermodynamicConstants.COMPONENTS.keys()
    if missing_components:
        raise ValueError(f"Missing component properties for: {missing_components}")
    return True


class TestThermodynamicConstants:
    def test_validate_components(self):
        """
        Verify that all components defined in FluidComposition have their properties defined.
        """
        assert validate_components()
