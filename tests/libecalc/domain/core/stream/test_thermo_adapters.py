from unittest.mock import Mock, patch

import pytest

from ecalc_neqsim_wrapper.thermo import NeqsimFluid
from libecalc.common.fluid import EoSModel
from libecalc.domain.process.core.stream.fluid import Fluid
from libecalc.domain.process.core.stream.thermo_adapters import NeqSimThermodynamicAdapter


@pytest.fixture
def mock_fluid():
    """Create a mocked domain Fluid for testing."""
    fluid = Mock(spec=Fluid)
    fluid.composition = Mock()
    fluid.eos_model = EoSModel.SRK
    return fluid


@pytest.fixture
def mock_neqsim_fluid():
    """Create a mocked NeqsimFluid for testing."""
    mock_fluid = Mock(spec=NeqsimFluid)
    mock_fluid.density = 50.0
    mock_fluid.enthalpy_joule_per_kg = 500000.0
    mock_fluid.z = 0.95
    mock_fluid.kappa = 1.3
    mock_fluid.molar_mass = 0.016  # Methane-like
    mock_fluid.set_new_pressure_and_temperature.return_value = mock_fluid
    mock_fluid.vapor_fraction_molar = 1.0
    return mock_fluid


class TestNeqSimThermodynamicAdapterUnit:
    """Unit tests for the NeqSimThermodynamicAdapter."""

    @patch("libecalc.domain.process.core.stream.thermo_adapters.NeqSimThermodynamicAdapter._create_neqsim_fluid")
    @patch("libecalc.domain.process.core.stream.thermo_adapters.NeqsimFluid")
    def test_all_properties(self, mock_neqsim_fluid_class, mock_create_neqsim_fluid, mock_fluid, mock_neqsim_fluid):
        """Test that all adapter methods correctly delegate to NeqsimFluid and return expected values."""
        # Arrange
        mock_create_neqsim_fluid.return_value = mock_neqsim_fluid
        mock_neqsim_fluid_class.create_thermo_system.return_value = mock_neqsim_fluid
        mock_neqsim_fluid.set_new_pressure_and_temperature.return_value = mock_neqsim_fluid

        adapter = NeqSimThermodynamicAdapter()
        pressure = 10.0
        temperature = 300.0

        # Act & Assert for each property
        # Density
        density = adapter.get_density(mock_fluid, pressure=pressure, temperature=temperature)
        assert density == 50.0
        mock_create_neqsim_fluid.assert_called_with(mock_fluid, pressure=pressure, temperature=temperature)

        # Enthalpy
        enthalpy = adapter.get_enthalpy(mock_fluid, pressure=pressure, temperature=temperature)
        assert enthalpy == 500000.0
        mock_create_neqsim_fluid.assert_called_with(mock_fluid, pressure=pressure, temperature=temperature)

        # Z-factor
        z = adapter.get_z(mock_fluid, pressure=pressure, temperature=temperature)
        assert z == 0.95
        mock_create_neqsim_fluid.assert_called_with(mock_fluid, pressure=pressure, temperature=temperature)

        # Kappa
        kappa = adapter.get_kappa(mock_fluid, pressure=pressure, temperature=temperature)
        assert kappa == 1.3
        mock_create_neqsim_fluid.assert_called_with(mock_fluid, pressure=pressure, temperature=temperature)

        # Molar mass (uses _create_neqsim_fluid with standard conditions)
        molar_mass = adapter.get_molar_mass(mock_fluid)
        assert molar_mass == 0.016
        mock_create_neqsim_fluid.assert_called_with(mock_fluid, pressure=1.01325, temperature=288.15)

        # Standard density (uses set_new_pressure_and_temperature)
        std_density = adapter.get_standard_density_gas_phase_after_flash(mock_fluid)
        assert std_density == 50.0  # Uses the same density property
        mock_neqsim_fluid_class.create_thermo_system.assert_called()

        # Vapor fraction
        vapor_fraction = adapter.get_vapor_fraction_molar(mock_fluid, pressure=pressure, temperature=temperature)
        assert vapor_fraction == 1.0


class TestNeqSimThermodynamicAdapterIntegration:
    """Integration tests for the NeqSimThermodynamicAdapter."""

    def test_thermodynamic_properties_at_specified_conditions(self, medium_composition):
        """Test the full thermodynamic property calculation pipeline.

        This test covers:
        1. Creating a NeqsimFluid from domain model
        2. Getting all properties via the adapter's interface
        3. Verifying expected values at specific conditions
        """
        # Arrange
        fluid = Fluid(composition=medium_composition, eos_model=EoSModel.SRK)
        adapter = NeqSimThermodynamicAdapter()
        pressure = 50.0
        temperature = 400.0

        # First test the direct creation of NeqsimFluid
        neqsim_fluid = adapter._create_neqsim_fluid(fluid, pressure=pressure, temperature=temperature)
        assert isinstance(neqsim_fluid, NeqsimFluid), "Should create a valid NeqsimFluid instance"

        # Get direct raw property values for comparison
        direct_density = neqsim_fluid.density
        direct_enthalpy = neqsim_fluid.enthalpy_joule_per_kg
        direct_z = neqsim_fluid.z
        direct_kappa = neqsim_fluid.kappa
        direct_molar_mass = neqsim_fluid.molar_mass
        direct_vapor_fraction = neqsim_fluid.vapor_fraction_molar

        # Act - now get all properties through the adapter interface
        density = adapter.get_density(fluid, pressure=pressure, temperature=temperature)
        enthalpy = adapter.get_enthalpy(fluid, pressure=pressure, temperature=temperature)
        z = adapter.get_z(fluid, pressure=pressure, temperature=temperature)
        kappa = adapter.get_kappa(fluid, pressure=pressure, temperature=temperature)
        molar_mass = adapter.get_molar_mass(fluid)
        std_density = adapter.get_standard_density_gas_phase_after_flash(fluid)
        vapor_fraction = adapter.get_vapor_fraction_molar(fluid, pressure=pressure, temperature=temperature)

        # Assert expected values match for both direct and adapter-mediated properties
        assert density == pytest.approx(direct_density), "Adapter should return same density as direct access"
        assert enthalpy == pytest.approx(direct_enthalpy), "Adapter should return same enthalpy as direct access"
        assert z == pytest.approx(direct_z), "Adapter should return same z-factor as direct access"
        assert kappa == pytest.approx(direct_kappa), "Adapter should return same kappa as direct access"
        assert molar_mass == pytest.approx(direct_molar_mass), "Adapter should return same molar mass as direct access"
        assert vapor_fraction == pytest.approx(
            direct_vapor_fraction
        ), "Adapter should return same vapor fraction as direct access"

        # Assert expected values at 50 bara and 400K from reference data
        assert density == pytest.approx(30.15, abs=0.5)  # kg/m3
        assert enthalpy == pytest.approx(239226, abs=5000)  # J/kg
        assert z == pytest.approx(0.972, abs=0.02)  # dimensionless
        assert kappa == pytest.approx(1.20, abs=0.1)  # dimensionless
        assert molar_mass == pytest.approx(0.0194, abs=0.001)  # kg/mol
        assert std_density == pytest.approx(0.825, abs=0.02)  # kg/m3
        assert vapor_fraction == pytest.approx(1.0, abs=0.01)  # dimensionless
