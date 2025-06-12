import pytest

from libecalc.domain.process.entities.fluid_stream.conditions import ProcessConditions
from libecalc.domain.process.entities.fluid_stream.eos_model import EoSModel
from libecalc.domain.process.entities.fluid_stream.exceptions import (
    IncompatibleEoSModelsException,
    IncompatibleThermoSystemProvidersException,
)
from libecalc.domain.process.entities.fluid_stream.fluid_composition import FluidComposition
from libecalc.domain.process.entities.fluid_stream.fluid_stream import FluidStream
from libecalc.domain.process.entities.fluid_stream.mixing import SimplifiedStreamMixing
from libecalc.infrastructure.thermo_system_providers.neqsim_thermo_system import NeqSimThermoSystem


class MockThermoSystem:
    """Mock thermo system for testing different providers."""

    def __init__(self, composition: FluidComposition, eos_model: EoSModel, conditions: ProcessConditions):
        self._composition = composition
        self._eos_model = eos_model
        self._conditions = conditions

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
        return 1000.0  # Mock value

    @property
    def enthalpy(self) -> float:
        return 50000.0  # Mock value

    @property
    def z(self) -> float:
        return 0.9  # Mock value

    @property
    def kappa(self) -> float:
        return 1.3  # Mock value

    @property
    def standard_density_gas_phase_after_flash(self) -> float:
        return 1.0  # Mock value

    @property
    def vapor_fraction_molar(self) -> float:
        return 1.0  # Mock value

    @property
    def molar_mass(self) -> float:
        return 0.020  # Mock value

    def flash_to_conditions(self, conditions: ProcessConditions, remove_liquid: bool = True):
        return MockThermoSystem(self._composition, self._eos_model, conditions)

    def flash_to_pressure_and_enthalpy_change(
        self, pressure_bara: float, enthalpy_change: float, remove_liquid: bool = True
    ):
        new_conditions = ProcessConditions(pressure_bara=pressure_bara, temperature_kelvin=self.temperature_kelvin)
        return MockThermoSystem(self._composition, self._eos_model, new_conditions)


class TestSimplifiedStreamMixing:
    """Test suite for the SimplifiedStreamMixing class."""

    def test_mix_medium_and_ultra_rich_compositions(self, medium_composition, ultra_rich_composition):
        """Test mixing medium and ultra rich compositions using SimplifiedStreamMixing."""
        # Define stream properties
        mass_rate_medium = 300.0  # kg/h
        mass_rate_ultra_rich = 700.0  # kg/h
        pressure = 15.0  # bara
        temperature = 310.0  # K
        eos_model = EoSModel.SRK

        # Create thermo systems
        conditions = ProcessConditions(pressure_bara=pressure, temperature_kelvin=temperature)
        medium_thermo = NeqSimThermoSystem(
            composition=medium_composition,
            eos_model=eos_model,
            conditions=conditions,
        )
        ultra_rich_thermo = NeqSimThermoSystem(
            composition=ultra_rich_composition,
            eos_model=eos_model,
            conditions=conditions,
        )

        # Create streams
        medium_stream = FluidStream(thermo_system=medium_thermo, mass_rate=mass_rate_medium)
        ultra_rich_stream = FluidStream(thermo_system=ultra_rich_thermo, mass_rate=mass_rate_ultra_rich)

        # Mix streams using SimplifiedStreamMixing strategy
        mixing_strategy = SimplifiedStreamMixing()
        mixed_stream = mixing_strategy.mix_streams([medium_stream, ultra_rich_stream])

        # Expected values from mixing medium (30%) and ultra rich (70%) compositions
        expected_values = {
            "nitrogen": 0.024873,
            "CO2": 0.010708,
            "methane": 0.706291,
            "ethane": 0.125049,
            "propane": 0.094894,
            "i_butane": 0.011998,
            "n_butane": 0.018507,
            "i_pentane": 0.003019,
            "n_pentane": 0.002583,
            "n_hexane": 0.002078,
            "water": 0.0,
        }

        # Verify mixed composition matches expected values
        mixed_composition = mixed_stream.thermo_system.composition
        for component, expected_value in expected_values.items():
            actual_value = getattr(mixed_composition, component)
            assert actual_value == pytest.approx(expected_value, abs=1e-5)

    def test_mix_streams_with_different_conditions(self, medium_composition):
        """Test mixing streams with different pressure and temperature conditions."""
        eos_model = EoSModel.SRK

        # Create thermo systems
        conditions1 = ProcessConditions(pressure_bara=20.0, temperature_kelvin=300.0)
        thermo1 = NeqSimThermoSystem(
            composition=medium_composition,
            eos_model=eos_model,
            conditions=conditions1,
        )

        conditions2 = ProcessConditions(pressure_bara=10.0, temperature_kelvin=350.0)
        thermo2 = NeqSimThermoSystem(
            composition=medium_composition,
            eos_model=eos_model,
            conditions=conditions2,
        )

        # Create streams
        stream1 = FluidStream(thermo_system=thermo1, mass_rate=500.0)
        stream2 = FluidStream(thermo_system=thermo2, mass_rate=500.0)

        # Mix streams
        mixing_strategy = SimplifiedStreamMixing()
        mixed_stream = mixing_strategy.mix_streams([stream1, stream2])

        # Verify the mixed stream uses the simplified mass-weighted average temperature and lowest pressure
        expected_temperature = (
            stream1.mass_rate * stream1.temperature_kelvin + stream2.mass_rate * stream2.temperature_kelvin
        ) / (stream1.mass_rate + stream2.mass_rate)

        assert mixed_stream.temperature_kelvin == expected_temperature
        assert mixed_stream.pressure_bara == stream2.pressure_bara
        assert mixed_stream.mass_rate == stream1.mass_rate + stream2.mass_rate

    def test_mix_streams_with_different_eos_models(self, medium_composition):
        """Test mixing streams with different EoS models raises IncompatibleEoSModelsException."""
        # Create thermo systems with different EoS models
        conditions = ProcessConditions(pressure_bara=15.0, temperature_kelvin=300.0)
        thermo1 = NeqSimThermoSystem(
            composition=medium_composition,
            eos_model=EoSModel.SRK,
            conditions=conditions,
        )
        thermo2 = NeqSimThermoSystem(
            composition=medium_composition,
            eos_model=EoSModel.PR,
            conditions=conditions,
        )

        # Create streams
        stream1 = FluidStream(thermo_system=thermo1, mass_rate=500.0)
        stream2 = FluidStream(thermo_system=thermo2, mass_rate=500.0)

        mixing_strategy = SimplifiedStreamMixing()

        with pytest.raises(IncompatibleEoSModelsException):
            mixing_strategy.mix_streams([stream1, stream2])

    def test_mix_streams_with_different_thermo_system_providers(self, medium_composition):
        """Test mixing streams with different thermo system providers raises IncompatibleThermoSystemProvidersException."""
        conditions = ProcessConditions(pressure_bara=15.0, temperature_kelvin=300.0)
        eos_model = EoSModel.SRK

        # Create one stream with NeqSimThermoSystem
        neqsim_thermo = NeqSimThermoSystem(
            composition=medium_composition,
            eos_model=eos_model,
            conditions=conditions,
        )
        neqsim_stream = FluidStream(thermo_system=neqsim_thermo, mass_rate=500.0)

        # Create another stream with MockThermoSystem (different provider)
        mock_thermo = MockThermoSystem(
            composition=medium_composition,
            eos_model=eos_model,
            conditions=conditions,
        )
        mock_stream = FluidStream(thermo_system=mock_thermo, mass_rate=500.0)  # type: ignore[arg-type] ignoring type mismatch for testing

        mixing_strategy = SimplifiedStreamMixing()

        with pytest.raises(IncompatibleThermoSystemProvidersException) as exc_info:
            mixing_strategy.mix_streams([neqsim_stream, mock_stream])

        # Verify the exception message contains the provider names
        assert "NeqSimThermoSystem" in str(exc_info.value)
        assert "MockThermoSystem" in str(exc_info.value)
