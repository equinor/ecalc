from unittest.mock import Mock, patch

import pytest

from ecalc_neqsim_wrapper.thermo import NeqsimFluid
from libecalc.common.fluid import EoSModel
from libecalc.domain.process.core.stream.conditions import ProcessConditions
from libecalc.domain.process.core.stream.thermo_system_adapter import NeqSimThermoSystem


class TestNeqSimThermoSystem:
    """Tests for the NeqSimThermoSystem implementation of ThermoSystemInterface."""

    def test_initialization_creates_neqsim_fluid(self, medium_composition):
        """Test that initialization creates a NeqsimFluid object internally."""
        with patch.object(NeqsimFluid, "create_thermo_system", return_value=Mock()) as mock_create:
            conditions = ProcessConditions(pressure_bara=10.0, temperature_kelvin=300.0)
            thermo_system = NeqSimThermoSystem(
                composition=medium_composition, eos_model=EoSModel.SRK, conditions=conditions
            )

            # Check NeqsimFluid.create_thermo_system was called with correct arguments
            mock_create.assert_called_once_with(
                composition=medium_composition, temperature_kelvin=300.0, pressure_bara=10.0, eos_model=EoSModel.SRK
            )

            # Check properties are correctly set
            assert thermo_system.composition == medium_composition
            assert thermo_system.eos_model == EoSModel.SRK
            assert thermo_system.pressure_bara == 10.0
            assert thermo_system.temperature_kelvin == 300.0

    def test_immutability(self, medium_composition):
        """Test that NeqSimThermoSystem is immutable (frozen dataclass)."""
        conditions = ProcessConditions(pressure_bara=10.0, temperature_kelvin=300.0)
        thermo_system = NeqSimThermoSystem(
            composition=medium_composition, eos_model=EoSModel.SRK, conditions=conditions
        )

        # Attempting to modify attributes should raise an exception
        with pytest.raises(Exception):
            thermo_system.pressure_bara = 20.0

        with pytest.raises(Exception):
            thermo_system.temperature_kelvin = 350.0

    def test_properties_cache(self, medium_composition):
        """Test that properties are cached."""
        with patch.object(NeqsimFluid, "create_thermo_system") as mock_create:
            # Create a mock fluid with property values
            mock_fluid = Mock()
            mock_fluid.density = 10.0
            mock_fluid.enthalpy_joule_per_kg = 1000.0
            mock_fluid.z = 0.9
            mock_fluid.kappa = 1.2
            mock_fluid.molar_mass = 0.016
            mock_fluid.vapor_fraction_molar = 1.0

            # Mock set_new_pressure_and_temperature to return another mock with density
            mock_std_fluid = Mock()
            mock_std_fluid.density = 0.7
            mock_fluid.set_new_pressure_and_temperature.return_value = mock_std_fluid

            # Set clone to return a copy of itself which will be used in standard_density calculation
            cloned_fluid = Mock()
            cloned_fluid.set_new_pressure_and_temperature.return_value = mock_std_fluid
            mock_fluid.copy.return_value = cloned_fluid

            # Make create_thermo_system return our mock fluid
            mock_create.return_value = mock_fluid

            # Create the thermo system
            conditions = ProcessConditions(pressure_bara=10.0, temperature_kelvin=300.0)
            thermo_system = NeqSimThermoSystem(
                composition=medium_composition, eos_model=EoSModel.SRK, conditions=conditions
            )

            # Access properties multiple times - should only compute once
            density1 = thermo_system.density
            density2 = thermo_system.density

            assert density1 == 10.0
            assert density2 == 10.0

            # Access other properties
            assert thermo_system.enthalpy == 1000.0
            assert thermo_system.z == 0.9
            assert thermo_system.kappa == 1.2
            assert thermo_system.molar_mass == 0.016
            assert thermo_system.vapor_fraction_molar == 1.0

            # Check standard_density_gas_phase_after_flash calls set_new_pressure_and_temperature
            std_density = thermo_system.standard_density_gas_phase_after_flash
            assert std_density == 0.7

            # Get standard conditions to verify
            std_conditions = ProcessConditions.standard_conditions()
            cloned_fluid.set_new_pressure_and_temperature.assert_called_once_with(
                new_pressure_bara=std_conditions.pressure_bara,
                new_temperature_kelvin=std_conditions.temperature_kelvin,
                remove_liquid=True,
            )

    def test_flash_to_conditions(self, medium_composition):
        """Test creating a new ThermoSystem with updated conditions and remove_liquid parameter."""
        # Create the original thermo system
        original_conditions = ProcessConditions(pressure_bara=10.0, temperature_kelvin=300.0)
        original_thermo = NeqSimThermoSystem(
            composition=medium_composition, eos_model=EoSModel.SRK, conditions=original_conditions
        )

        # Test with default remove_liquid=True
        new_pressure = 20.0
        new_temperature = 350.0
        new_conditions = ProcessConditions(pressure_bara=new_pressure, temperature_kelvin=new_temperature)
        new_thermo = original_thermo.flash_to_conditions(conditions=new_conditions)

        # Verify new thermo system has updated conditions but same composition/eos
        assert new_thermo.pressure_bara == new_pressure
        assert new_thermo.temperature_kelvin == new_temperature
        assert new_thermo.composition == original_thermo.composition
        assert new_thermo.eos_model == original_thermo.eos_model

        # Verify it's a different object
        assert new_thermo is not original_thermo

        # Original should be unchanged
        assert original_thermo.pressure_bara == 10.0
        assert original_thermo.temperature_kelvin == 300.0

        # Now test with explicit remove_liquid=False using a different approach
        # Create a completely fresh test with mocked NeqsimFluid
        with patch.object(NeqsimFluid, "create_thermo_system") as mock_create:
            # Setup the initial Mock fluid
            mock_initial_fluid = Mock()
            mock_create.return_value = mock_initial_fluid

            # Setup the copy and flash result
            mock_copy = Mock()
            mock_initial_fluid.copy.return_value = mock_copy

            mock_flashed_fluid = Mock()
            mock_copy.set_new_pressure_and_temperature.return_value = mock_flashed_fluid

            # Create a test thermo system
            test_conditions = ProcessConditions(pressure_bara=5.0, temperature_kelvin=280.0)
            test_thermo = NeqSimThermoSystem(
                composition=medium_composition, eos_model=EoSModel.SRK, conditions=test_conditions
            )

            # Flash with remove_liquid=False
            flash_conditions = ProcessConditions(pressure_bara=8.0, temperature_kelvin=290.0)
            test_thermo.flash_to_conditions(conditions=flash_conditions, remove_liquid=False)

            # Verify the correct parameters were passed
            mock_copy.set_new_pressure_and_temperature.assert_called_once_with(
                new_pressure_bara=8.0, new_temperature_kelvin=290.0, remove_liquid=False
            )

    def test_integration_properties_at_conditions(self, medium_composition):
        """Integration test checking properties at specific conditions."""
        # Create a thermo system at 50 bara and 400K
        pressure = 50.0
        temperature = 400.0
        conditions = ProcessConditions(pressure_bara=pressure, temperature_kelvin=temperature)
        thermo_system = NeqSimThermoSystem(
            composition=medium_composition,
            eos_model=EoSModel.SRK,
            conditions=conditions,
        )

        # Check property values against reference values
        assert thermo_system.density == pytest.approx(30.15, abs=0.5)  # kg/m3
        assert thermo_system.enthalpy == pytest.approx(239226, abs=5000)  # J/kg
        assert thermo_system.z == pytest.approx(0.972, abs=0.02)  # dimensionless
        assert thermo_system.kappa == pytest.approx(1.20, abs=0.1)  # dimensionless
        assert thermo_system.molar_mass == pytest.approx(0.0194, abs=0.001)  # kg/mol
        assert thermo_system.standard_density_gas_phase_after_flash == pytest.approx(0.825, abs=0.02)  # kg/m3
        assert thermo_system.vapor_fraction_molar == pytest.approx(1.0, abs=0.01)  # dimensionless

    def test_direct_vs_property_access(self, medium_composition):
        """Test that property access correctly delegates to the underlying NeqsimFluid object."""
        # Create a real thermo system with a real NeqsimFluid
        pressure = 50.0
        temperature = 400.0
        conditions = ProcessConditions(pressure_bara=pressure, temperature_kelvin=temperature)
        thermo_system = NeqSimThermoSystem(
            composition=medium_composition,
            eos_model=EoSModel.SRK,
            conditions=conditions,
        )

        # Get direct access to the NeqsimFluid for comparison
        fluid = thermo_system._neqsim_fluid

        # Check that properties match the direct fluid properties
        assert thermo_system.density == pytest.approx(fluid.density)
        assert thermo_system.enthalpy == pytest.approx(fluid.enthalpy_joule_per_kg)
        assert thermo_system.z == pytest.approx(fluid.z)
        assert thermo_system.kappa == pytest.approx(fluid.kappa)
        assert thermo_system.molar_mass == pytest.approx(fluid.molar_mass)
        assert thermo_system.vapor_fraction_molar == pytest.approx(fluid.vapor_fraction_molar)

        # For standard density, we need to verify against a fluid at standard conditions
        std_conditions = ProcessConditions.standard_conditions()
        std_fluid = fluid.set_new_pressure_and_temperature(
            new_pressure_bara=std_conditions.pressure_bara,
            new_temperature_kelvin=std_conditions.temperature_kelvin,
            remove_liquid=True,
        )
        assert thermo_system.standard_density_gas_phase_after_flash == pytest.approx(std_fluid.density)
