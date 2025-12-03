import pytest

from libecalc.domain.process.value_objects.fluid_stream.exceptions import (
    IncompatibleEoSModelsException,
)
from libecalc.domain.process.value_objects.fluid_stream.fluid_model import EoSModel, FluidModel
from libecalc.domain.process.value_objects.fluid_stream.fluid_stream import FluidStream
from libecalc.domain.process.value_objects.fluid_stream.mixing import SimplifiedStreamMixing


class TestSimplifiedStreamMixing:
    """Test suite for the SimplifiedStreamMixing class.

    These tests use the NeqSimFluidService and require the JVM to be running.
    """

    def test_mix_medium_and_ultra_rich_compositions(self, medium_composition, ultra_rich_composition):
        """Test mixing medium and ultra rich compositions using SimplifiedStreamMixing."""
        from ecalc_neqsim_wrapper.fluid_service import NeqSimFluidService

        # Define stream properties
        mass_rate_medium = 300.0  # kg/h
        mass_rate_ultra_rich = 700.0  # kg/h
        pressure = 15.0  # bara
        temperature = 310.0  # K
        eos_model = EoSModel.SRK

        # Create fluid models
        medium_model = FluidModel(composition=medium_composition, eos_model=eos_model)
        ultra_rich_model = FluidModel(composition=ultra_rich_composition, eos_model=eos_model)

        # Get properties via service
        service = NeqSimFluidService.instance()
        medium_props = service.get_properties(medium_model, pressure, temperature, remove_liquid=False)
        ultra_rich_props = service.get_properties(ultra_rich_model, pressure, temperature, remove_liquid=False)

        # Create streams
        medium_stream = FluidStream(fluid_model=medium_model, fluid_properties=medium_props, mass_rate_kg_per_h=mass_rate_medium)
        ultra_rich_stream = FluidStream(fluid_model=ultra_rich_model, fluid_properties=ultra_rich_props, mass_rate_kg_per_h=mass_rate_ultra_rich)

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
        mixed_composition = mixed_stream.composition
        for component, expected_value in expected_values.items():
            actual_value = getattr(mixed_composition, component)
            assert actual_value == pytest.approx(expected_value, abs=1e-5)

    def test_mix_streams_with_different_conditions(self, medium_composition):
        """Test mixing streams with different pressure and temperature conditions."""
        from ecalc_neqsim_wrapper.fluid_service import NeqSimFluidService

        eos_model = EoSModel.SRK

        # Create fluid model
        fluid_model = FluidModel(composition=medium_composition, eos_model=eos_model)

        # Get properties via service at different conditions
        service = NeqSimFluidService.instance()
        props1 = service.get_properties(fluid_model, pressure_bara=20.0, temperature_kelvin=300.0, remove_liquid=False)
        props2 = service.get_properties(fluid_model, pressure_bara=10.0, temperature_kelvin=350.0, remove_liquid=False)

        # Create streams
        stream1 = FluidStream(fluid_model=fluid_model, fluid_properties=props1, mass_rate_kg_per_h=500.0)
        stream2 = FluidStream(fluid_model=fluid_model, fluid_properties=props2, mass_rate_kg_per_h=500.0)

        # Mix streams
        mixing_strategy = SimplifiedStreamMixing()
        mixed_stream = mixing_strategy.mix_streams([stream1, stream2])

        # Verify the mixed stream uses the simplified mass-weighted average temperature and lowest pressure
        expected_temperature = (
            stream1.mass_rate_kg_per_h * stream1.temperature_kelvin
            + stream2.mass_rate_kg_per_h * stream2.temperature_kelvin
        ) / (stream1.mass_rate_kg_per_h + stream2.mass_rate_kg_per_h)

        assert mixed_stream.temperature_kelvin == expected_temperature
        assert mixed_stream.pressure_bara == stream2.pressure_bara
        assert mixed_stream.mass_rate_kg_per_h == stream1.mass_rate_kg_per_h + stream2.mass_rate_kg_per_h

    def test_mix_streams_with_different_eos_models(self, medium_composition):
        """Test mixing streams with different EoS models raises IncompatibleEoSModelsException."""
        from ecalc_neqsim_wrapper.fluid_service import NeqSimFluidService

        pressure = 15.0
        temperature = 300.0

        # Create fluid models with different EoS
        srk_model = FluidModel(composition=medium_composition, eos_model=EoSModel.SRK)
        pr_model = FluidModel(composition=medium_composition, eos_model=EoSModel.PR)

        # Get properties via service
        service = NeqSimFluidService.instance()
        srk_props = service.get_properties(srk_model, pressure, temperature, remove_liquid=False)
        pr_props = service.get_properties(pr_model, pressure, temperature, remove_liquid=False)

        # Create streams
        stream1 = FluidStream(fluid_model=srk_model, fluid_properties=srk_props, mass_rate_kg_per_h=500.0)
        stream2 = FluidStream(fluid_model=pr_model, fluid_properties=pr_props, mass_rate_kg_per_h=500.0)

        mixing_strategy = SimplifiedStreamMixing()

        with pytest.raises(IncompatibleEoSModelsException):
            mixing_strategy.mix_streams([stream1, stream2])
