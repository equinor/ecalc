from dataclasses import FrozenInstanceError
from unittest.mock import Mock

import pytest

from libecalc.common.fluid import EoSModel
from libecalc.domain.process.core.stream.fluid import Fluid


@pytest.fixture
def mock_thermodynamic_engine():
    """Create a mock thermodynamic engine for testing."""
    mock_engine = Mock()
    mock_engine.get_molar_mass.return_value = 0.016  # e.g., methane-like
    return mock_engine


class TestFluid:
    def test_init_requires_engine(self, medium_composition, mock_thermodynamic_engine):
        """
        Since Fluid no longer creates a default engine,
        we must supply one at init time. This test verifies that.
        """
        fluid = Fluid(
            composition=medium_composition, eos_model=EoSModel.PR, _thermodynamic_engine=mock_thermodynamic_engine
        )
        assert fluid.composition == medium_composition
        assert fluid.eos_model == EoSModel.PR
        assert fluid._thermodynamic_engine == mock_thermodynamic_engine

    def test_molar_mass_calls_engine(self, medium_composition, mock_thermodynamic_engine):
        """The Fluid should delegate molar_mass calculation to the supplied engine."""
        fluid = Fluid(composition=medium_composition, _thermodynamic_engine=mock_thermodynamic_engine)
        assert fluid.molar_mass == 0.016
        mock_thermodynamic_engine.get_molar_mass.assert_called_once_with(fluid)

    def test_fluid_frozen_dataclass(self, medium_composition, mock_thermodynamic_engine):
        """Verify that Fluid is a frozen dataclass."""
        fluid = Fluid(composition=medium_composition, _thermodynamic_engine=mock_thermodynamic_engine)
        with pytest.raises(FrozenInstanceError):
            fluid.eos_model = EoSModel.PR  # Attempt to mutate
