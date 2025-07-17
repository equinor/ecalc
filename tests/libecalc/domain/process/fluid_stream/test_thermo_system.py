from unittest.mock import Mock, patch

import pytest

from ecalc_neqsim_wrapper.thermo import NeqsimFluid
from libecalc.domain.process.value_objects.fluid_stream.fluid_model import EoSModel
from libecalc.domain.process.value_objects.fluid_stream.process_conditions import ProcessConditions
from libecalc.infrastructure.thermo_system_providers.neqsim_thermo_system import NeqSimThermoSystem


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
            # Note: composition is normalized before being passed to create_thermo_system
            mock_create.assert_called_once_with(
                composition=medium_composition.normalized(),
                temperature_kelvin=300.0,
                pressure_bara=10.0,
                eos_model=EoSModel.SRK,
            )

            # Check properties are correctly set and that composition is normalized
            assert thermo_system.composition == medium_composition.normalized()
            assert thermo_system.eos_model == EoSModel.SRK
            assert thermo_system.pressure_bara == 10.0
            assert thermo_system.temperature_kelvin == 300.0

    def test_initialization_with_neqsim_fluid(self, medium_composition):
        """Test initialization with a provided NeqsimFluid object."""
        mock_fluid = Mock()
        conditions = ProcessConditions(pressure_bara=10.0, temperature_kelvin=300.0)

        with patch.object(NeqsimFluid, "create_thermo_system", return_value=Mock()) as mock_create:
            thermo_system = NeqSimThermoSystem(
                composition=medium_composition, eos_model=EoSModel.SRK, conditions=conditions, neqsim_fluid=mock_fluid
            )

            # Check that create_thermo_system was not called
            mock_create.assert_not_called()

            # Check that the provided fluid was used
            assert thermo_system._neqsim_fluid is mock_fluid

    def test_immutability(self, medium_composition):
        """Test that NeqSimThermoSystem attributes are effectively immutable."""
        conditions = ProcessConditions(pressure_bara=10.0, temperature_kelvin=300.0)
        thermo_system = NeqSimThermoSystem(
            composition=medium_composition, eos_model=EoSModel.SRK, conditions=conditions
        )

        # Attempting to modify public property attributes should raise an exception
        with pytest.raises(AttributeError):
            thermo_system.pressure_bara = 20.0

        with pytest.raises(AttributeError):
            thermo_system.temperature_kelvin = 350.0

        # Attempting to modify private attributes should raise an exception
        with pytest.raises(AttributeError):
            thermo_system._composition = medium_composition

        with pytest.raises(AttributeError):
            thermo_system._eos_model = EoSModel.PR

        with pytest.raises(AttributeError):
            thermo_system._conditions = conditions

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

        # Test with remove_liquid=False to preserve composition
        new_pressure = 20.0
        new_temperature = 350.0
        new_conditions = ProcessConditions(pressure_bara=new_pressure, temperature_kelvin=new_temperature)
        new_thermo = original_thermo.flash_to_conditions(conditions=new_conditions, remove_liquid=False)

        # Verify new thermo system has updated conditions but same composition/eos
        assert new_thermo.pressure_bara == new_pressure
        assert new_thermo.temperature_kelvin == new_temperature
        assert new_thermo.composition == original_thermo.composition

        # Test with remove_liquid=True (default), which should update the composition only if liquid is present
        # The T,P conditions in the test should be such that no liquid is formed
        # Such that vapor_fraction_molar == 1, then compositions should approximately match
        # Account for potential differences wrt. neqsim output with approximate equality
        # Compare each component individually to avoid comparing class instances directly
        new_thermo_liquid_removed = original_thermo.flash_to_conditions(conditions=new_conditions, remove_liquid=True)
        assert new_thermo_liquid_removed.pressure_bara == new_pressure
        assert new_thermo_liquid_removed.temperature_kelvin == new_temperature
        for component in medium_composition.__dict__:
            assert getattr(original_thermo.composition, component) == pytest.approx(
                getattr(new_thermo_liquid_removed.composition, component), abs=1e-6
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
