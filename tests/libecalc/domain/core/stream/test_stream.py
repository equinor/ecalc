from unittest.mock import Mock

import pytest

from libecalc.common.fluid import EoSModel
from libecalc.common.units import UnitConstants
from libecalc.domain.process.core.stream.conditions import ProcessConditions
from libecalc.domain.process.core.stream.exceptions import NegativeMassRateException
from libecalc.domain.process.core.stream.stream import Stream
from libecalc.domain.process.core.stream.thermo_system import NeqSimThermoSystem, ThermoSystemInterface


@pytest.fixture
def mock_thermo_system():
    """Create a mock ThermoSystemInterface for testing."""
    mock = Mock(spec=ThermoSystemInterface)
    mock.pressure_bara = 20.0
    mock.temperature_kelvin = 310.0
    mock.density = 50.0
    mock.molar_mass = 0.018
    mock.standard_density_gas_phase_after_flash = 0.8
    mock.enthalpy = 10000.0
    mock.z = 0.8
    mock.kappa = 1.3
    mock.vapor_fraction_molar = 1.0

    # Mock the conditions property
    conditions = ProcessConditions(pressure_bara=20.0, temperature_kelvin=310.0)
    mock.conditions = conditions

    # Mock the flash_to_conditions method to return a new mock
    new_mock = Mock(spec=ThermoSystemInterface)
    new_mock.pressure_bara = 15.0
    new_mock.temperature_kelvin = 350.0
    new_mock.density = 40.0
    new_mock.molar_mass = 0.018
    new_mock.standard_density_gas_phase_after_flash = 0.8
    new_mock.enthalpy = 12000.0
    new_mock.z = 0.85
    new_mock.kappa = 1.35
    new_mock.vapor_fraction_molar = 1.0
    new_conditions = ProcessConditions(pressure_bara=15.0, temperature_kelvin=350.0)
    new_mock.conditions = new_conditions

    mock.flash_to_conditions.return_value = new_mock

    # Mock the flash_to_pressure_and_enthalpy_change method
    ph_mock = Mock(spec=ThermoSystemInterface)
    ph_mock.pressure_bara = 5.0
    ph_mock.temperature_kelvin = 290.0  # Cooled due to enthalpy change
    ph_mock.density = 55.0
    ph_mock.molar_mass = 0.018
    ph_mock.standard_density_gas_phase_after_flash = 0.8
    ph_mock.enthalpy = 5000.0  # Reduced enthalpy
    ph_mock.z = 0.82
    ph_mock.kappa = 1.32
    ph_mock.vapor_fraction_molar = 1.0
    ph_conditions = ProcessConditions(pressure_bara=5.0, temperature_kelvin=290.0)
    ph_mock.conditions = ph_conditions

    mock.flash_to_pressure_and_enthalpy_change.return_value = ph_mock

    return mock


@pytest.fixture
def basic_stream(medium_composition):
    """Create a basic stream using NeqSimThermoSystem."""
    conditions = ProcessConditions(pressure_bara=10.0, temperature_kelvin=300.0)
    thermo_system = NeqSimThermoSystem(composition=medium_composition, eos_model=EoSModel.SRK, conditions=conditions)
    return Stream(thermo_system=thermo_system, mass_rate=1000.0)


class TestStream:
    """Test suite for the Stream class."""

    def test_init_and_basic_properties(self, mock_thermo_system):
        """Test initialization and basic property accessors."""
        stream = Stream(thermo_system=mock_thermo_system, mass_rate=100.0)

        # Verify basic attributes
        assert stream.thermo_system is mock_thermo_system
        assert stream.mass_rate == 100.0

        # Verify property accessors
        assert stream.temperature_kelvin == 310.0
        assert stream.pressure_bara == 20.0
        assert stream.conditions == mock_thermo_system.conditions

    def test_create_stream_with_new_conditions(self, mock_thermo_system):
        """Test creating a new stream with modified conditions."""
        stream = Stream(thermo_system=mock_thermo_system, mass_rate=100.0)

        # Create new conditions
        new_conditions = ProcessConditions(pressure_bara=15.0, temperature_kelvin=350.0)

        # Test with default remove_liquid=True
        new_stream = stream.create_stream_with_new_conditions(conditions=new_conditions)

        # Verify that flash_to_conditions was called correctly
        mock_thermo_system.flash_to_conditions.assert_called_once_with(conditions=new_conditions, remove_liquid=True)

        # Reset the mock to test with explicit remove_liquid=False
        mock_thermo_system.flash_to_conditions.reset_mock()

        # Test with explicit remove_liquid=False
        new_stream = stream.create_stream_with_new_conditions(conditions=new_conditions, remove_liquid=False)

        # Verify flash_to_conditions was called with remove_liquid=False
        mock_thermo_system.flash_to_conditions.assert_called_once_with(conditions=new_conditions, remove_liquid=False)

        # Verify new stream properties
        assert new_stream.pressure_bara == 15.0
        assert new_stream.temperature_kelvin == 350.0
        assert new_stream.mass_rate == 100.0

    def test_negative_mass_rate_exception(self, mock_thermo_system):
        """Test that NegativeMassRateException is raised for negative mass rate."""
        with pytest.raises(NegativeMassRateException):
            Stream(thermo_system=mock_thermo_system, mass_rate=-100.0)

    def test_thermodynamic_properties(self, mock_thermo_system):
        """Test that Stream properties correctly forward to the ThermoSystem."""
        stream = Stream(thermo_system=mock_thermo_system, mass_rate=100.0)

        # Test direct property forwarding
        assert stream.density == mock_thermo_system.density
        assert stream.molar_mass == mock_thermo_system.molar_mass
        assert (
            stream.standard_density_gas_phase_after_flash == mock_thermo_system.standard_density_gas_phase_after_flash
        )
        assert stream.enthalpy == mock_thermo_system.enthalpy
        assert stream.z == mock_thermo_system.z
        assert stream.kappa == mock_thermo_system.kappa
        assert stream.vapor_fraction_molar == mock_thermo_system.vapor_fraction_molar

        # Test calculated properties
        assert stream.volumetric_rate == stream.mass_rate / mock_thermo_system.density
        assert (
            stream.standard_rate
            == (stream.mass_rate / mock_thermo_system.standard_density_gas_phase_after_flash)
            * UnitConstants.HOURS_PER_DAY
        )

    def test_create_stream_with_new_pressure_and_enthalpy_change(self, mock_thermo_system):
        """Test create_stream_with_new_pressure_and_enthalpy_change method."""
        stream = Stream(thermo_system=mock_thermo_system, mass_rate=100.0)

        new_pressure = 5.0  # bara
        enthalpy_change = -5000.0  # J/kg (cooling)

        # Call the method
        new_stream = stream.create_stream_with_new_pressure_and_enthalpy_change(
            pressure_bara=new_pressure, enthalpy_change=enthalpy_change
        )

        # Verify the thermo system method was called with correct parameters
        mock_thermo_system.flash_to_pressure_and_enthalpy_change.assert_called_once_with(
            pressure_bara=new_pressure, enthalpy_change=enthalpy_change, remove_liquid=True
        )

        # Verify properties of the new stream
        assert new_stream.pressure_bara == 5.0
        assert new_stream.temperature_kelvin == 290.0
        assert new_stream.enthalpy == 5000.0
        assert new_stream.mass_rate == 100.0

    def test_from_standard_rate(self, mock_thermo_system):
        """Test creating a stream from standard rate."""
        # Setup test inputs
        standard_rate = 240.0  # Sm³/day

        # Create stream using class method
        stream = Stream.from_standard_rate(
            standard_rate=standard_rate,
            thermo_system=mock_thermo_system,
        )

        # Check that the stream has the correct properties
        assert isinstance(stream, Stream)
        assert stream.thermo_system is mock_thermo_system  # Same object, not a copy

        # Calculate expected mass rate
        expected_mass_rate = (
            standard_rate * mock_thermo_system.standard_density_gas_phase_after_flash / UnitConstants.HOURS_PER_DAY
        )
        assert stream.mass_rate == expected_mass_rate
