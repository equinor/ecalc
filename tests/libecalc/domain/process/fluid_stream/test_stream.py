from unittest.mock import MagicMock

import pytest

from libecalc.common.units import UnitConstants
from libecalc.domain.process.value_objects.fluid_stream.exceptions import NegativeMassRateException
from libecalc.domain.process.value_objects.fluid_stream.fluid import Fluid
from libecalc.domain.process.value_objects.fluid_stream.fluid_stream import FluidStream
from tests.libecalc.domain.process.conftest import create_mock_fluid_properties


class TestStream:
    def test_init_and_basic_properties(self, mock_fluid):
        stream = FluidStream(fluid=mock_fluid, mass_rate_kg_per_h=100.0)

        assert stream.pressure_bara == 20.0
        assert stream.temperature_kelvin == 310.0
        assert stream.conditions.pressure_bara == 20.0
        assert stream.conditions.temperature_kelvin == 310.0
        assert stream.mass_rate_kg_per_h == 100.0

    def test_pt_flash_pattern_via_service(self, mock_fluid):
        """Test PT-flash pattern: create_fluid + with_new_fluid."""
        stream = FluidStream(fluid=mock_fluid, mass_rate_kg_per_h=100.0)

        # Create mock properties for the result
        new_props = create_mock_fluid_properties(
            pressure_bara=15.0,
            temperature_kelvin=350.0,
        )

        # Mock the service
        mock_service = MagicMock()
        new_fluid = Fluid(fluid_model=mock_fluid.fluid_model, properties=new_props)
        mock_service.create_fluid.return_value = new_fluid

        # Call the pattern: create_fluid + with_new_fluid
        result_fluid = mock_service.create_fluid(
            stream.fluid_model,
            15.0,
            350.0,
        )
        updated = stream.with_new_fluid(result_fluid)

        assert updated.pressure_bara == 15.0
        assert updated.temperature_kelvin == 350.0
        assert updated.mass_rate_kg_per_h == 100.0
        # Original stream unchanged
        assert stream.pressure_bara == 20.0
        assert stream.temperature_kelvin == 310.0

    def test_negative_mass_rate_exception(self, mock_fluid):
        with pytest.raises(NegativeMassRateException):
            FluidStream(fluid=mock_fluid, mass_rate_kg_per_h=-100.0)

    def test_thermodynamic_properties(self, mock_fluid):
        stream = FluidStream(fluid=mock_fluid, mass_rate_kg_per_h=100.0)

        assert stream.density == 50.0
        assert stream.molar_mass == 0.018
        assert stream.standard_density_gas_phase_after_flash == 0.8
        assert stream.enthalpy_joule_per_kg == 10000.0
        assert stream.z == 0.8
        assert stream.kappa == 1.3
        assert stream.vapor_fraction_molar == 1.0

        assert stream.volumetric_rate_m3_per_hour == 100.0 / 50.0
        assert stream.standard_rate_sm3_per_day == (100.0 / 0.8) * UnitConstants.HOURS_PER_DAY

    def test_ph_flash_pattern_via_service(self, mock_fluid_model, mock_fluid_properties_factory):
        """Test PH-flash pattern: flash_ph + construct Fluid + with_new_fluid."""
        # Create a custom system with different initial conditions for this test
        props = mock_fluid_properties_factory(
            pressure_bara=10.0, temperature_kelvin=300.0, enthalpy_joule_per_kg=10000.0
        )
        fluid = Fluid(fluid_model=mock_fluid_model, properties=props)
        stream = FluidStream(fluid=fluid, mass_rate_kg_per_h=100.0)

        new_pressure = 5.0
        enthalpy_change = -5000.0
        target_enthalpy = stream.enthalpy_joule_per_kg + enthalpy_change
        expected_temp = 300.0 + (enthalpy_change / 1000.0)

        # Create mock properties for the result
        new_props = create_mock_fluid_properties(
            pressure_bara=new_pressure,
            temperature_kelvin=expected_temp,
            enthalpy_joule_per_kg=target_enthalpy,
        )

        # Mock the service
        mock_service = MagicMock()
        mock_service.flash_ph.return_value = new_props

        # Call the pattern: flash_ph + construct Fluid + with_new_fluid
        result_props = mock_service.flash_ph(stream.fluid_model, new_pressure, target_enthalpy)
        new_fluid = Fluid(fluid_model=stream.fluid_model, properties=result_props)
        new_stream = stream.with_new_fluid(new_fluid)

        assert new_stream.pressure_bara == 5.0
        assert new_stream.temperature_kelvin == expected_temp
        assert new_stream.mass_rate_kg_per_h == 100.0

    def test_from_standard_rate(self, mock_fluid_model, mock_fluid_properties_factory):
        # Create a custom system with different initial conditions for this test
        props = mock_fluid_properties_factory(pressure_bara=10.0, temperature_kelvin=300.0)
        result = FluidStream.from_standard_rate(
            standard_rate_m3_per_day=240.0, fluid_model=mock_fluid_model, fluid_properties=props
        )

        assert result.mass_rate_kg_per_h == (240.0 * 0.8) / 24.0
        assert result.pressure_bara == 10.0
        assert result.temperature_kelvin == 300.0

    def test_with_new_fluid(self, mock_fluid, mock_fluid_properties_factory):
        """Test the with_new_fluid method preserves mass rate."""
        stream = FluidStream(fluid=mock_fluid, mass_rate_kg_per_h=100.0)

        new_props = mock_fluid_properties_factory(
            pressure_bara=15.0,
            temperature_kelvin=350.0,
        )
        new_fluid = Fluid(fluid_model=mock_fluid.fluid_model, properties=new_props)

        updated = stream.with_new_fluid(new_fluid)

        assert updated.pressure_bara == 15.0
        assert updated.temperature_kelvin == 350.0
        assert updated.mass_rate_kg_per_h == 100.0
        # Original stream unchanged
        assert stream.pressure_bara == 20.0
        assert stream.temperature_kelvin == 310.0
