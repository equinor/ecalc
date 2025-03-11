import pytest

from libecalc.common.fluid import EoSModel
from libecalc.domain.process.core.stream.conditions import ProcessConditions
from libecalc.domain.process.core.stream.fluid import Fluid
from libecalc.domain.process.core.stream.mixing import SimplifiedStreamMixing
from libecalc.domain.process.core.stream.stream import Stream


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

        # Create fluid objects
        medium_fluid = Fluid(composition=medium_composition, eos_model=eos_model)
        ultra_rich_fluid = Fluid(composition=ultra_rich_composition, eos_model=eos_model)

        # Create stream objects
        conditions = ProcessConditions(temperature=temperature, pressure=pressure)
        medium_stream = Stream(fluid=medium_fluid, conditions=conditions, mass_rate=mass_rate_medium)
        ultra_rich_stream = Stream(fluid=ultra_rich_fluid, conditions=conditions, mass_rate=mass_rate_ultra_rich)

        # Mix streams using SimplifiedStreamMixing strategy
        mixing_strategy = SimplifiedStreamMixing()
        mixed_stream = mixing_strategy.mix_streams([medium_stream, ultra_rich_stream])

        # Expected values from mixing medium (30%) and ultra rich (70%) compositions
        expected_values = {
            "nitrogen": 2.487276589996555,
            "CO2": 1.0707871730843908,
            "methane": 70.62911715314632,
            "ethane": 12.504902973680636,
            "propane": 9.489383653583825,
            "i_butane": 1.1997997038567125,
            "n_butane": 1.8507228295685063,
            "i_pentane": 0.3018819517169132,
            "n_pentane": 0.2583407880707626,
            "n_hexane": 0.20778894297432215,
            "water": 0.0,
        }

        # Verify mixed composition matches expected values
        mixed_composition = mixed_stream.fluid.composition
        for component, expected_value in expected_values.items():
            actual_value = getattr(mixed_composition, component)
            assert actual_value == pytest.approx(expected_value, abs=1e-10)

    def test_mix_streams_with_different_conditions(self, medium_composition):
        """Test mixing streams with different pressure and temperature conditions."""
        # Create two streams with the same composition but different conditions
        eos_model = EoSModel.SRK
        fluid = Fluid(composition=medium_composition, eos_model=eos_model)

        # Stream 1: High pressure, low temperature
        conditions1 = ProcessConditions(temperature=300.0, pressure=20.0)
        stream1 = Stream(fluid=fluid, conditions=conditions1, mass_rate=500.0)

        # Stream 2: Low pressure, high temperature
        conditions2 = ProcessConditions(temperature=350.0, pressure=10.0)
        stream2 = Stream(fluid=fluid, conditions=conditions2, mass_rate=500.0)

        # Mix streams
        mixing_strategy = SimplifiedStreamMixing()
        mixed_stream = mixing_strategy.mix_streams([stream1, stream2])

        # Verify the mixed stream uses the first stream's temperature and lowest pressure
        assert mixed_stream.temperature == stream1.temperature
        assert mixed_stream.pressure == stream2.pressure
        assert mixed_stream.mass_rate == stream1.mass_rate + stream2.mass_rate

    def test_mix_streams_with_different_eos_models(self, medium_composition):
        """Test mixing streams with different EoS models raises ValueError."""
        # Create two streams with different EoS models
        fluid1 = Fluid(composition=medium_composition, eos_model=EoSModel.SRK)
        fluid2 = Fluid(composition=medium_composition, eos_model=EoSModel.PR)

        conditions = ProcessConditions(temperature=300.0, pressure=15.0)
        stream1 = Stream(fluid=fluid1, conditions=conditions, mass_rate=500.0)
        stream2 = Stream(fluid=fluid2, conditions=conditions, mass_rate=500.0)

        mixing_strategy = SimplifiedStreamMixing()

        with pytest.raises(ValueError, match="Cannot mix streams with different EoS models"):
            mixing_strategy.mix_streams([stream1, stream2])
