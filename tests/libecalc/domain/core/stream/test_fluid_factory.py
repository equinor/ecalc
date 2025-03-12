from unittest.mock import patch

from libecalc.common.fluid import EoSModel
from libecalc.domain.process.core.stream.fluid_factory import create_fluid_with_neqsim_engine
from libecalc.domain.process.core.stream.thermo_adapters import NeqSimThermodynamicAdapter


def test_create_fluid_with_neqsim_engine(medium_composition):
    """Ensure factory creates a Fluid with a NeqSim engine and default EoS if not specified."""

    with patch.object(NeqSimThermodynamicAdapter, "__init__", return_value=None) as mock_adapter_init:
        fluid = create_fluid_with_neqsim_engine(medium_composition)

        # Check the adapter was instantiated
        mock_adapter_init.assert_called_once()

    assert fluid.composition == medium_composition
    assert fluid.eos_model == EoSModel.SRK  # default if not provided
    assert fluid.molar_mass  # calls the adapter behind the scenes
    # There's no fluid._engine_type or fluid._thermodynamic_engine == None anymore


def test_create_fluid_with_neqsim_engine_custom_eos(medium_composition):
    """Check the factory respects a custom EoS if provided."""
    fluid = create_fluid_with_neqsim_engine(medium_composition, eos_model=EoSModel.PR)

    assert fluid.eos_model == EoSModel.PR
