import pytest

from libecalc.common.fluid import EoSModel
from libecalc.domain.process.core.stream.conditions import ProcessConditions
from libecalc.domain.process.core.stream.exceptions import IncompatibleEoSModelsException
from libecalc.domain.process.core.stream.mixing import SimplifiedStreamMixing
from libecalc.domain.process.core.stream.stream import Stream
from libecalc.domain.process.core.stream.thermo_system import NeqSimThermoSystem


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
        medium_stream = Stream(thermo_system=medium_thermo, mass_rate=mass_rate_medium)
        ultra_rich_stream = Stream(thermo_system=ultra_rich_thermo, mass_rate=mass_rate_ultra_rich)

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
        stream1 = Stream(thermo_system=thermo1, mass_rate=500.0)
        stream2 = Stream(thermo_system=thermo2, mass_rate=500.0)

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
        stream1 = Stream(thermo_system=thermo1, mass_rate=500.0)
        stream2 = Stream(thermo_system=thermo2, mass_rate=500.0)

        mixing_strategy = SimplifiedStreamMixing()

        with pytest.raises(IncompatibleEoSModelsException):
            mixing_strategy.mix_streams([stream1, stream2])
