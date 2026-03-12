import pytest

from libecalc.domain.process.entities.process_units.mixer.mixer import Mixer
from libecalc.domain.process.process_system.process_system import ProcessSystem
from libecalc.domain.process.value_objects.fluid_stream import (
    Fluid,
    FluidModel,
    FluidProperties,
    FluidService,
    FluidStream,
)


class DummyFluidService(FluidService):
    def flash_pt(self, fluid_model: FluidModel, pressure_bara: float, temperature_kelvin: float) -> FluidProperties:
        pass

    def flash_ph(self, fluid_model: FluidModel, pressure_bara: float, target_enthalpy: float) -> FluidProperties:
        pass

    def remove_liquid(self, fluid: Fluid) -> Fluid:
        pass

    def create_fluid(self, fluid_model: FluidModel, pressure_bara: float, temperature_kelvin: float) -> Fluid:
        pass

    def create_stream_from_standard_rate(
        self, fluid_model: FluidModel, pressure_bara: float, temperature_kelvin: float, standard_rate_m3_per_day: float
    ) -> FluidStream:
        pass

    def create_stream_from_mass_rate(
        self, fluid_model: FluidModel, pressure_bara: float, temperature_kelvin: float, mass_rate_kg_per_h: float
    ) -> FluidStream:
        pass

    def standard_rate_to_mass_rate(self, fluid_model: FluidModel, standard_rate_m3_per_day: float) -> float:
        pass

    def mass_rate_to_standard_rate(self, fluid_model: FluidModel, mass_rate_kg_per_h: float) -> float:
        pass


@pytest.fixture
def fluid_service() -> FluidService:
    return DummyFluidService()


def test_recirculation_loop_around_splitter_raises_valueerror(
    splitter_factory, fluid_service, recirculation_loop_factory
):
    process_unit = splitter_factory(number_of_outputs=2)
    with pytest.raises(ValueError, match="Inner process cannot be a splitter"):
        recirculation_loop_factory(inner_process=process_unit)


def test_recirculation_loop_around_mixer_raises_valueerror(
    fluid_service,
    recirculation_loop_factory,
):
    process_unit = Mixer(number_of_inputs=2, fluid_service=fluid_service)
    with pytest.raises(ValueError, match="Inner process cannot be a mixer"):
        recirculation_loop_factory(inner_process=process_unit)


def test_recirculation_loop_around_process_system_with_multiple_streams_raises_valueerror(
    choke_factory,
    liquid_remover_factory,
    recirculation_loop_factory,
    fluid_service,
):
    liquid_remover = liquid_remover_factory()
    choke = choke_factory(pressure_change=2)
    mixer = Mixer(number_of_inputs=2, fluid_service=fluid_service)
    process_system = ProcessSystem(process_units=[liquid_remover, choke, mixer])
    with pytest.raises(ValueError, match="Inner process cannot have multiple streams"):
        recirculation_loop_factory(inner_process=process_system)
