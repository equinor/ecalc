from dataclasses import FrozenInstanceError
from unittest.mock import Mock, patch

import pytest

from libecalc.common.fluid import EoSModel, FluidComposition
from libecalc.domain.process.core.stream.fluid import Fluid


@pytest.fixture
def mock_thermodynamic_engine():
    """Create a mock thermodynamic engine for testing."""
    mock_engine = Mock()
    mock_engine.get_molar_mass.return_value = 0.016  # Methane-like molar mass (kg/mol)
    return mock_engine


class TestFluid:
    """Test suite for the Fluid class."""

    def test_init_default(self, medium_composition):
        """Test that a Fluid can be initialized with default settings."""
        fluid = Fluid(composition=medium_composition)

        # Verify default values
        assert fluid.composition == medium_composition
        assert fluid.eos_model == EoSModel.SRK
        assert fluid._engine_type == "neqsim"
        assert fluid._thermodynamic_engine is not None

    def test_with_neqsim_engine_factory(self, medium_composition):
        """Test the factory method for creating a Fluid with NeqSim engine."""
        fluid = Fluid.with_neqsim_engine(composition=medium_composition)

        # Verify factory method sets correct values
        assert fluid.composition == medium_composition
        assert fluid.eos_model == EoSModel.SRK
        assert fluid._engine_type == "neqsim"
        assert fluid._thermodynamic_engine is not None

    def test_custom_eos_model(self, medium_composition):
        """Test that a Fluid can be initialized with a custom EoS model."""
        fluid = Fluid(composition=medium_composition, eos_model=EoSModel.PR)

        # Verify custom EoS model
        assert fluid.eos_model == EoSModel.PR

    @patch("libecalc.domain.process.core.stream.thermo_adapters.NeqSimThermodynamicAdapter")
    def test_thermodynamic_engine_initialization(self, mock_adapter_class, medium_composition):
        """Test that the thermodynamic engine is properly initialized."""
        mock_adapter = Mock()
        mock_adapter_class.return_value = mock_adapter

        fluid = Fluid(composition=medium_composition)

        # Verify the mock adapter was used
        assert fluid._thermodynamic_engine is mock_adapter

    def test_custom_thermodynamic_engine_and_molar_mass(self, medium_composition, mock_thermodynamic_engine):
        """Test that:
        1. A custom thermodynamic engine can be provided during initialization
        2. The molar_mass property correctly calls get_molar_mass on the engine
        """
        # Create fluid with a pre-configured engine (passed during initialization)
        fluid = Fluid(composition=medium_composition, _thermodynamic_engine=mock_thermodynamic_engine)

        # Verify the engine was used directly without creating a new one
        assert fluid._thermodynamic_engine == mock_thermodynamic_engine

        # Call the molar_mass property
        molar_mass = fluid.molar_mass

        # Verify the property correctly calls get_molar_mass on the engine
        mock_thermodynamic_engine.get_molar_mass.assert_called_once_with(fluid)
        assert molar_mass == 0.016  # The mocked return value

    def test_fluid_frozen_dataclass(self, medium_composition):
        """Test that Fluid is a frozen dataclass that cannot be modified after creation."""
        fluid = Fluid(composition=medium_composition)

        # Attempting to modify the fluid should raise an exception
        with pytest.raises(FrozenInstanceError):
            fluid.composition = FluidComposition(methane=90.0, ethane=10.0)
