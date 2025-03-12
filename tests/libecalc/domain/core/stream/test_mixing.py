from unittest.mock import Mock

import pytest

from libecalc.common.fluid import EoSModel
from libecalc.domain.process.core.stream.conditions import ProcessConditions
from libecalc.domain.process.core.stream.fluid import Fluid, ThermodynamicEngine
from libecalc.domain.process.core.stream.fluid_factory import create_fluid_with_neqsim_engine
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
        medium_fluid = create_fluid_with_neqsim_engine(composition=medium_composition, eos_model=eos_model)
        ultra_rich_fluid = create_fluid_with_neqsim_engine(composition=ultra_rich_composition, eos_model=eos_model)

        # Create stream objects
        conditions = ProcessConditions(temperature=temperature, pressure=pressure)
        medium_stream = Stream(fluid=medium_fluid, conditions=conditions, mass_rate=mass_rate_medium)
        ultra_rich_stream = Stream(fluid=ultra_rich_fluid, conditions=conditions, mass_rate=mass_rate_ultra_rich)

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
        mixed_composition = mixed_stream.fluid.composition
        for component, expected_value in expected_values.items():
            actual_value = getattr(mixed_composition, component)
            assert actual_value == pytest.approx(expected_value, abs=1e-5)

    def test_mix_streams_with_different_conditions(self, medium_composition):
        """Test mixing streams with different pressure and temperature conditions."""
        eos_model = EoSModel.SRK
        fluid = create_fluid_with_neqsim_engine(composition=medium_composition, eos_model=eos_model)

        # Stream 1: High pressure, low temperature
        conditions1 = ProcessConditions(temperature=300.0, pressure=20.0)
        stream1 = Stream(fluid=fluid, conditions=conditions1, mass_rate=500.0)

        # Stream 2: Low pressure, high temperature
        conditions2 = ProcessConditions(temperature=350.0, pressure=10.0)
        stream2 = Stream(fluid=fluid, conditions=conditions2, mass_rate=500.0)

        # Mix streams
        mixing_strategy = SimplifiedStreamMixing()
        mixed_stream = mixing_strategy.mix_streams([stream1, stream2])

        # Verify the mixed stream uses the simplified mass-weighted average temperature and lowest pressure
        expected_temperature = (
            stream1.mass_rate * stream1.conditions.temperature + stream2.mass_rate * stream2.conditions.temperature
        ) / (stream1.mass_rate + stream2.mass_rate)

        assert mixed_stream.conditions.temperature == expected_temperature
        assert mixed_stream.conditions.pressure == stream2.conditions.pressure
        assert mixed_stream.mass_rate == stream1.mass_rate + stream2.mass_rate

    def test_mix_streams_with_different_eos_models(self, medium_composition):
        """Test mixing streams with different EoS models raises ValueError."""
        # Create two streams with different EoS models
        fluid1 = create_fluid_with_neqsim_engine(composition=medium_composition, eos_model=EoSModel.SRK)
        fluid2 = create_fluid_with_neqsim_engine(composition=medium_composition, eos_model=EoSModel.PR)

        conditions = ProcessConditions(temperature=300.0, pressure=15.0)
        stream1 = Stream(fluid=fluid1, conditions=conditions, mass_rate=500.0)
        stream2 = Stream(fluid=fluid2, conditions=conditions, mass_rate=500.0)

        mixing_strategy = SimplifiedStreamMixing()

        with pytest.raises(ValueError, match="Cannot mix streams with different EoS models"):
            mixing_strategy.mix_streams([stream1, stream2])

    def test_mix_streams_engine_override(self, medium_composition):
        """
        Verify that if no engine is provided, the result inherits from the first stream;
        if a custom engine is provided, it is used for the mixed Fluid.
        """
        # We'll mock out the engine references to confirm which one the new fluid picks
        mock_engine_first = Mock(spec=ThermodynamicEngine)
        mock_engine_second = Mock(spec=ThermodynamicEngine)

        # Ensure get_molar_mass returns a numeric value
        mock_engine_first.get_molar_mass.return_value = 0.018
        mock_engine_second.get_molar_mass.return_value = 0.018

        # Create two fluids with the same EoS model but different engine objects
        eos_model = EoSModel.SRK
        fluid1 = Fluid(composition=medium_composition, eos_model=eos_model, _thermodynamic_engine=mock_engine_first)
        fluid2 = Fluid(composition=medium_composition, eos_model=eos_model, _thermodynamic_engine=mock_engine_second)

        conditions = ProcessConditions(temperature=300.0, pressure=20.0)
        stream1 = Stream(fluid=fluid1, conditions=conditions, mass_rate=100.0)
        stream2 = Stream(fluid=fluid2, conditions=conditions, mass_rate=100.0)

        mixing_strategy = SimplifiedStreamMixing()

        # Case 1: No engine override => inherits engine from the first stream
        mixed_stream_inherited = mixing_strategy.mix_streams([stream1, stream2])
        assert mixed_stream_inherited.fluid._thermodynamic_engine is mock_engine_first

        # Case 2: Provide a custom engine
        custom_engine = Mock(spec=ThermodynamicEngine)
        custom_engine.get_molar_mass.return_value = 0.018  # Must also return a float
        mixed_stream_custom = mixing_strategy.mix_streams([stream1, stream2], engine=custom_engine)
        assert mixed_stream_custom.fluid._thermodynamic_engine is custom_engine
