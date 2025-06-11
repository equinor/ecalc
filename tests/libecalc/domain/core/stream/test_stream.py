import pytest

from libecalc.common.fluid import EoSModel
from libecalc.common.units import UnitConstants
from libecalc.domain.process.entities.fluid_stream.conditions import ProcessConditions
from libecalc.domain.process.entities.fluid_stream.exceptions import NegativeMassRateException
from libecalc.domain.process.entities.fluid_stream.fluid_stream import FluidStream
from libecalc.domain.process.entities.fluid_stream.thermo_system import ThermoSystemInterface


class FakeThermoSystem(ThermoSystemInterface):
    """
    Minimal interface implementation that stores pressure and temperature in memory
    and updates them when flash methods are called. Other properties return placeholders.
    """

    def __init__(self, pressure_bara: float, temperature_kelvin: float):
        self._pressure = pressure_bara
        self._temperature = temperature_kelvin

    @property
    def conditions(self):
        return ProcessConditions(pressure_bara=self._pressure, temperature_kelvin=self._temperature)

    @property
    def pressure_bara(self) -> float:
        return self._pressure

    @property
    def temperature_kelvin(self) -> float:
        return self._temperature

    @property
    def composition(self):
        return None

    @property
    def eos_model(self):
        return EoSModel.SRK

    @property
    def density(self) -> float:
        return 50.0

    @property
    def molar_mass(self) -> float:
        return 0.018

    @property
    def standard_density_gas_phase_after_flash(self) -> float:
        return 0.8

    @property
    def enthalpy(self) -> float:
        return 10000.0

    @property
    def z(self) -> float:
        return 0.8

    @property
    def kappa(self) -> float:
        return 1.3

    @property
    def vapor_fraction_molar(self) -> float:
        return 1.0

    def flash_to_conditions(self, conditions: ProcessConditions, remove_liquid: bool = True):
        return FakeThermoSystem(
            pressure_bara=conditions.pressure_bara, temperature_kelvin=conditions.temperature_kelvin
        )

    def flash_to_pressure_and_enthalpy_change(
        self, pressure_bara: float, enthalpy_change: float, remove_liquid: bool = True
    ):
        new_temp = self._temperature + (enthalpy_change / 1000.0)
        return FakeThermoSystem(pressure_bara=pressure_bara, temperature_kelvin=new_temp)


class TestStream:
    def test_init_and_basic_properties(self):
        system = FakeThermoSystem(pressure_bara=20.0, temperature_kelvin=310.0)
        stream = FluidStream(thermo_system=system, mass_rate=100.0)

        assert stream.pressure_bara == 20.0
        assert stream.temperature_kelvin == 310.0
        assert stream.conditions.pressure_bara == 20.0
        assert stream.conditions.temperature_kelvin == 310.0
        assert stream.mass_rate == 100.0

    def test_create_stream_with_new_conditions(self):
        system = FakeThermoSystem(pressure_bara=20.0, temperature_kelvin=310.0)
        stream = FluidStream(thermo_system=system, mass_rate=100.0)

        new_cond = ProcessConditions(pressure_bara=15.0, temperature_kelvin=350.0)
        updated = stream.create_stream_with_new_conditions(conditions=new_cond)

        assert updated.pressure_bara == 15.0
        assert updated.temperature_kelvin == 350.0
        assert updated.mass_rate == 100.0
        assert stream.pressure_bara == 20.0
        assert stream.temperature_kelvin == 310.0

    def test_negative_mass_rate_exception(self):
        system = FakeThermoSystem(pressure_bara=20.0, temperature_kelvin=310.0)
        with pytest.raises(NegativeMassRateException):
            FluidStream(thermo_system=system, mass_rate=-100.0)

    def test_thermodynamic_properties(self):
        system = FakeThermoSystem(pressure_bara=20.0, temperature_kelvin=310.0)
        stream = FluidStream(thermo_system=system, mass_rate=100.0)

        assert stream.density == 50.0
        assert stream.molar_mass == 0.018
        assert stream.standard_density_gas_phase_after_flash == 0.8
        assert stream.enthalpy == 10000.0
        assert stream.z == 0.8
        assert stream.kappa == 1.3
        assert stream.vapor_fraction_molar == 1.0

        assert stream.volumetric_rate == 100.0 / 50.0
        assert stream.standard_rate == (100.0 / 0.8) * UnitConstants.HOURS_PER_DAY

    def test_create_stream_with_new_pressure_and_enthalpy_change(self):
        system = FakeThermoSystem(pressure_bara=10.0, temperature_kelvin=300.0)
        stream = FluidStream(thermo_system=system, mass_rate=100.0)

        new_pressure = 5.0
        enthalpy_change = -5000.0
        new_stream = stream.create_stream_with_new_pressure_and_enthalpy_change(
            pressure_bara=new_pressure, enthalpy_change=enthalpy_change
        )

        expected_temp = 300.0 + (enthalpy_change / 1000.0)
        assert new_stream.pressure_bara == 5.0
        assert new_stream.temperature_kelvin == expected_temp
        assert new_stream.mass_rate == 100.0

    def test_from_standard_rate(self):
        system = FakeThermoSystem(pressure_bara=10.0, temperature_kelvin=300.0)
        result = FluidStream.from_standard_rate(standard_rate=240.0, thermo_system=system)

        assert result.mass_rate == (240.0 * 0.8) / 24.0
        assert result.pressure_bara == 10.0
        assert result.temperature_kelvin == 300.0
