import pytest

from libecalc.domain.process.value_objects.fluid_stream.fluid_model import EoSModel, FluidComposition
from libecalc.domain.process.value_objects.fluid_stream.fluid_stream import FluidStream
from libecalc.domain.process.value_objects.fluid_stream.process_conditions import ProcessConditions
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


class MockThermoSystem(ThermoSystemInterface):
    """Mock thermo system for testing different providers."""

    def __init__(
        self,
        composition: FluidComposition | None = None,
        eos_model: EoSModel = EoSModel.SRK,
        conditions: ProcessConditions | None = None,
    ):
        self._composition = composition or FluidComposition(methane=1.0)  # Default simple composition
        self._eos_model = eos_model
        self._conditions = conditions or ProcessConditions(pressure_bara=20.0, temperature_kelvin=310.0)

    @property
    def composition(self) -> FluidComposition:
        return self._composition

    @property
    def eos_model(self) -> EoSModel:
        return self._eos_model

    @property
    def conditions(self) -> ProcessConditions:
        return self._conditions

    @property
    def pressure_bara(self) -> float:
        return self._conditions.pressure_bara

    @property
    def temperature_kelvin(self) -> float:
        return self._conditions.temperature_kelvin

    @property
    def density(self) -> float:
        return 50.0  # Mock value

    @property
    def molar_mass(self) -> float:
        return 0.018  # Mock value

    @property
    def standard_density_gas_phase_after_flash(self) -> float:
        return 0.8  # Mock value

    @property
    def enthalpy(self) -> float:
        return 10000.0  # Mock value

    @property
    def z(self) -> float:
        return 0.8  # Mock value

    @property
    def kappa(self) -> float:
        return 1.3  # Mock value

    @property
    def vapor_fraction_molar(self) -> float:
        return 1.0  # Mock value

    def flash_to_conditions(self, conditions: ProcessConditions, remove_liquid: bool = True):
        return MockThermoSystem(self._composition, self._eos_model, conditions)

    def flash_to_pressure_and_enthalpy_change(
        self, pressure_bara: float, enthalpy_change: float, remove_liquid: bool = True
    ):
        new_temp = self.temperature_kelvin + (enthalpy_change / 1000.0)
        new_conditions = ProcessConditions(pressure_bara=pressure_bara, temperature_kelvin=new_temp)
        return MockThermoSystem(self._composition, self._eos_model, new_conditions)


@pytest.fixture
def mock_thermo_system(medium_composition) -> MockThermoSystem:
    """Create a mock thermo system for testing."""
    conditions = ProcessConditions(pressure_bara=20.0, temperature_kelvin=310.0)
    return MockThermoSystem(composition=medium_composition, eos_model=EoSModel.SRK, conditions=conditions)


@pytest.fixture
def mock_thermo_system_factory(medium_composition):
    """Factory to create mock thermo systems with custom P and T."""

    def factory(pressure_bara: float, temperature_kelvin: float):
        conditions = ProcessConditions(pressure_bara=pressure_bara, temperature_kelvin=temperature_kelvin)
        return MockThermoSystem(composition=medium_composition, eos_model=EoSModel.SRK, conditions=conditions)

    return factory


@pytest.fixture
def fluid_stream_mock(mock_thermo_system) -> FluidStream:
    """Create a mocked fluid stream for testing."""
    return FluidStream(thermo_system=mock_thermo_system, mass_rate_kg_per_h=100.0)
