from unittest.mock import Mock

import pytest

from libecalc.common.fluid import EoSModel
from libecalc.domain.process.core.stream.conditions import ProcessConditions
from libecalc.domain.process.core.stream.exceptions import NegativeMassRateException
from libecalc.domain.process.core.stream.fluid_factory import create_fluid_with_neqsim_engine
from libecalc.domain.process.core.stream.stream import Stream


@pytest.fixture
def mock_fluid():
    """Create a mock fluid for testing."""
    fluid = Mock(spec=create_fluid_with_neqsim_engine)
    return fluid


@pytest.fixture
def basic_stream(medium_composition):
    """Create a basic stream for testing."""
    eos_model = EoSModel.SRK
    fluid = create_fluid_with_neqsim_engine(composition=medium_composition, eos_model=eos_model)
    conditions = ProcessConditions(temperature_kelvin=300.0, pressure_bara=10.0)
    return Stream(fluid=fluid, conditions=conditions, mass_rate=1000.0)


class TestStream:
    """Test suite for the Stream class."""

    def test_init_and_basic_properties(self, mock_fluid):
        """Test initialization and basic property accessors."""
        conditions = ProcessConditions(temperature_kelvin=310.0, pressure_bara=20.0)
        stream = Stream(fluid=mock_fluid, conditions=conditions, mass_rate=100.0)

        # Verify basic attributes
        assert stream.fluid is mock_fluid
        assert stream.conditions is conditions
        assert stream.mass_rate == 100.0

        # Verify property accessors
        assert stream.temperature == 310.0
        assert stream.pressure == 20.0

    def test_create_stream_with_new_conditions(self, basic_stream):
        """Test creating a new stream with modified conditions."""
        new_conditions = ProcessConditions(temperature_kelvin=350.0, pressure_bara=15.0)

        new_stream = basic_stream.create_stream_with_new_conditions(new_conditions)

        # Verify new stream has the new conditions but same fluid
        assert new_stream.temperature == 350.0
        assert new_stream.pressure == 15.0
        assert new_stream.fluid is basic_stream.fluid

    def test_negative_mass_rate_exception(self, mock_fluid):
        """Test that NegativeMassRateException is raised for negative mass rate."""
        conditions = ProcessConditions(temperature_kelvin=310.0, pressure_bara=20.0)
        with pytest.raises(NegativeMassRateException):
            Stream(fluid=mock_fluid, conditions=conditions, mass_rate=-100.0)

    def test_thermodynamic_properties(self, mock_fluid):
        """Test that Stream properties correctly use the fluid's thermodynamic engine."""
        # Setup test values
        mock_density = 50.0
        mock_molar_mass = 20.0
        mock_std_density = 0.8
        mock_enthalpy = 10000.0
        mock_z = 0.8
        mock_kappa = 1.3
        test_temperature = 310.0
        test_pressure = 20.0
        mass_rate_test = 100.0

        # Setup mock thermodynamic engine
        mock_thermo_engine = Mock()
        mock_fluid._thermodynamic_engine = mock_thermo_engine

        # Configure return values for the mock engine
        mock_thermo_engine.get_density.return_value = mock_density
        mock_thermo_engine.get_molar_mass.return_value = mock_molar_mass
        mock_thermo_engine.get_standard_density_gas_phase_after_flash.return_value = mock_std_density
        mock_thermo_engine.get_enthalpy.return_value = mock_enthalpy
        mock_thermo_engine.get_z.return_value = mock_z
        mock_thermo_engine.get_kappa.return_value = mock_kappa

        # Create stream with mocked fluid
        conditions = ProcessConditions(temperature_kelvin=test_temperature, pressure_bara=test_pressure)
        stream = Stream(fluid=mock_fluid, conditions=conditions, mass_rate=mass_rate_test)

        # Test direct properties
        assert stream.density == mock_density
        mock_thermo_engine.get_density.assert_called_once_with(
            mock_fluid, pressure=test_pressure, temperature=test_temperature
        )

        assert stream.molar_mass == mock_molar_mass
        mock_thermo_engine.get_molar_mass.assert_called_once_with(mock_fluid)

        assert stream.standard_density_gas_phase_after_flash == mock_std_density
        mock_thermo_engine.get_standard_density_gas_phase_after_flash.assert_called_once_with(mock_fluid)

        assert stream.enthalpy == mock_enthalpy
        mock_thermo_engine.get_enthalpy.assert_called_once_with(
            mock_fluid, pressure=test_pressure, temperature=test_temperature
        )

        assert stream.z == mock_z
        mock_thermo_engine.get_z.assert_called_once_with(
            mock_fluid, pressure=test_pressure, temperature=test_temperature
        )

        assert stream.kappa == mock_kappa
        mock_thermo_engine.get_kappa.assert_called_once_with(
            mock_fluid, pressure=test_pressure, temperature=test_temperature
        )

        # Test derived properties
        assert stream.volumetric_rate == mass_rate_test / mock_density  # mass_rate / density
        assert (
            stream.standard_rate == (mass_rate_test / mock_std_density) * 24
        )  # (mass_rate / std_density) * hours_per_day

    def test_from_standard_rate(self, mock_fluid):
        """Test creating a stream from standard rate."""
        # Setup test values
        mock_std_density = 0.8
        test_temperature = 310.0
        test_pressure = 20.0
        standard_rate = 240.0  # Sm³/day
        hours_per_day = 24  # UnitConstants.HOURS_PER_DAY

        # Setup mock thermodynamic engine
        mock_thermo_engine = Mock()
        mock_fluid._thermodynamic_engine = mock_thermo_engine
        mock_thermo_engine.get_standard_density_gas_phase_after_flash.return_value = mock_std_density

        conditions = ProcessConditions(temperature_kelvin=test_temperature, pressure_bara=test_pressure)

        # Create stream using from_standard_rate
        stream = Stream.from_standard_rate(fluid=mock_fluid, conditions=conditions, standard_rate=standard_rate)

        # Check that the correct methods were called
        mock_thermo_engine.get_standard_density_gas_phase_after_flash.assert_called_once_with(mock_fluid)

        # Check that mass_rate was calculated correctly (standard_rate * std_density / hours_per_day)
        expected_mass_rate = standard_rate * mock_std_density / hours_per_day
        assert stream.mass_rate == expected_mass_rate
