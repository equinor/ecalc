import pytest

from libecalc.domain.process.value_objects.fluid_stream.conditions import ProcessConditions
from libecalc.domain.process.value_objects.fluid_stream.eos_model import EoSModel
from libecalc.domain.process.value_objects.fluid_stream.fluid_composition import FluidComposition
from libecalc.domain.process.value_objects.fluid_stream.fluid_stream import FluidStream
from libecalc.domain.process.value_objects.fluid_stream.thermo_system import ThermoSystemInterface


@pytest.fixture
def medium_composition() -> FluidComposition:
    """Create a medium gas composition (19.4 kg/kmol) for testing.
    This matches the predefined MEDIUM_MW_19P4 composition."""
    return FluidComposition(
        nitrogen=0.74373,
        CO2=2.415619,
        methane=85.60145,
        ethane=6.707826,
        propane=2.611471,
        i_butane=0.45077,
        n_butane=0.691702,
        i_pentane=0.210714,
        n_pentane=0.197937,
        n_hexane=0.368786,
    )


@pytest.fixture
def ultra_rich_composition() -> FluidComposition:
    """Create an ultra rich gas composition (24.6 kg/kmol) for testing.
    This matches the predefined ULTRA_RICH_MW_24P6 composition."""
    return FluidComposition(
        nitrogen=3.433045573,
        CO2=0.341296928,
        methane=62.50752861,
        ethane=15.64946798,
        propane=13.2202369,
        i_butane=1.606103192,
        n_butane=2.479421803,
        i_pentane=0.351335073,
        n_pentane=0.291106204,
        n_hexane=0.120457739,
    )


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

    def flash_to_conditions(self, conditions: ProcessConditions, remove_liquid: bool = False):
        return FakeThermoSystem(
            pressure_bara=conditions.pressure_bara, temperature_kelvin=conditions.temperature_kelvin
        )

    def flash_to_pressure_and_enthalpy_change(
        self, pressure_bara: float, enthalpy_change: float, remove_liquid: bool = False
    ):
        new_temp = self._temperature + (enthalpy_change / 1000.0)
        return FakeThermoSystem(pressure_bara=pressure_bara, temperature_kelvin=new_temp)


@pytest.fixture
def fake_thermo_system() -> FakeThermoSystem:
    """Create a fake thermo system for testing."""
    return FakeThermoSystem(pressure_bara=20.0, temperature_kelvin=310.0)


@pytest.fixture
def fake_thermo_system_factory():
    """Factory to create fake thermo systems with custom parameters."""
    return FakeThermoSystem


@pytest.fixture
def fluid_stream_mock(fake_thermo_system) -> FluidStream:
    """Create a mocked fluid stream for testing."""
    return FluidStream(thermo_system=fake_thermo_system, mass_rate=100.0)
