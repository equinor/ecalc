import pytest

from libecalc.common.units import UnitConstants
from libecalc.domain.process.value_objects.fluid_stream.exceptions import NegativeMassRateException
from libecalc.domain.process.value_objects.fluid_stream.fluid_stream import FluidStream
from libecalc.domain.process.value_objects.fluid_stream.process_conditions import ProcessConditions


class TestStream:
    def test_init_and_basic_properties(self, mock_thermo_system):
        stream = FluidStream(thermo_system=mock_thermo_system, mass_rate_kg_per_h=100.0)

        assert stream.pressure_bara == 20.0
        assert stream.temperature_kelvin == 310.0
        assert stream.conditions.pressure_bara == 20.0
        assert stream.conditions.temperature_kelvin == 310.0
        assert stream.mass_rate_kg_per_h == 100.0

    def test_create_stream_with_new_conditions(self, mock_thermo_system):
        stream = FluidStream(thermo_system=mock_thermo_system, mass_rate_kg_per_h=100.0)

        new_cond = ProcessConditions(pressure_bara=15.0, temperature_kelvin=350.0)
        updated = stream.create_stream_with_new_conditions(conditions=new_cond)

        assert updated.pressure_bara == 15.0
        assert updated.temperature_kelvin == 350.0
        assert updated.mass_rate_kg_per_h == 100.0
        assert stream.pressure_bara == 20.0
        assert stream.temperature_kelvin == 310.0

    def test_negative_mass_rate_exception(self, mock_thermo_system):
        with pytest.raises(NegativeMassRateException):
            FluidStream(thermo_system=mock_thermo_system, mass_rate_kg_per_h=-100.0)

    def test_thermodynamic_properties(self, mock_thermo_system):
        stream = FluidStream(thermo_system=mock_thermo_system, mass_rate_kg_per_h=100.0)

        assert stream.density == 50.0
        assert stream.molar_mass == 0.018
        assert stream.standard_density_gas_phase_after_flash == 0.8
        assert stream.enthalpy == 10000.0
        assert stream.z == 0.8
        assert stream.kappa == 1.3
        assert stream.vapor_fraction_molar == 1.0

        assert stream.volumetric_rate == 100.0 / 50.0
        assert stream.standard_rate == (100.0 / 0.8) * UnitConstants.HOURS_PER_DAY

    def test_create_stream_with_new_pressure_and_enthalpy_change(self, mock_thermo_system_factory):
        # Create a custom system with different initial conditions for this test
        system = mock_thermo_system_factory(pressure_bara=10.0, temperature_kelvin=300.0)
        stream = FluidStream(thermo_system=system, mass_rate_kg_per_h=100.0)

        new_pressure = 5.0
        enthalpy_change = -5000.0
        new_stream = stream.create_stream_with_new_pressure_and_enthalpy_change(
            pressure_bara=new_pressure, enthalpy_change_joule_per_kg=enthalpy_change
        )

        expected_temp = 300.0 + (enthalpy_change / 1000.0)
        assert new_stream.pressure_bara == 5.0
        assert new_stream.temperature_kelvin == expected_temp
        assert new_stream.mass_rate_kg_per_h == 100.0

    def test_from_standard_rate(self, mock_thermo_system_factory):
        # Create a custom system with different initial conditions for this test
        system = mock_thermo_system_factory(pressure_bara=10.0, temperature_kelvin=300.0)
        result = FluidStream.from_standard_rate(standard_rate_m3_per_day=240.0, thermo_system=system)

        assert result.mass_rate_kg_per_h == (240.0 * 0.8) / 24.0
        assert result.pressure_bara == 10.0
        assert result.temperature_kelvin == 300.0
