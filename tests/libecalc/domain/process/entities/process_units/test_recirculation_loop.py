import uuid

import pytest
from inline_snapshot import snapshot

from libecalc.domain.component_validation_error import DomainValidationException
from libecalc.domain.process.entities.process_units.legacy_mixer.legacy_mixer import LegacyMixer
from libecalc.domain.process.entities.process_units.legacy_splitter.legacy_splitter import (
    LegacySplitter,
)
from libecalc.domain.process.entities.process_units.mixer import Mixer
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


@pytest.mark.inlinesnapshot
@pytest.mark.snapshot
def test_recirculation_loop_around_splitter_raises_exception(fluid_service, recirculation_loop_factory):
    process_unit = LegacySplitter(number_of_outputs=2)
    with pytest.raises(Exception) as exc_info:
        recirculation_loop_factory(inner_process=process_unit)

    assert str(exc_info.value) == snapshot("Recirculation loop should contain a ProcessSystem")


@pytest.mark.inlinesnapshot
@pytest.mark.snapshot
def test_recirculation_loop_around_mixer_raises_exception(
    fluid_service,
    recirculation_loop_factory,
):
    process_unit = LegacyMixer(number_of_inputs=2, fluid_service=fluid_service)
    with pytest.raises(Exception) as exc_info:
        recirculation_loop_factory(inner_process=process_unit)

    assert str(exc_info.value) == snapshot("Recirculation loop should contain a ProcessSystem")


@pytest.mark.inlinesnapshot
@pytest.mark.snapshot
def test_recirculation_loop_around_process_system_with_multiple_streams_raises_exception(
    choke_factory,
    liquid_remover_factory,
    recirculation_loop_factory,
    fluid_service,
    process_system_factory,
):
    liquid_remover = liquid_remover_factory()
    choke = choke_factory(pressure_change=2)
    mixer = Mixer(process_unit_id=uuid.uuid4(), fluid_service=fluid_service)
    process_system = process_system_factory(process_units=[liquid_remover, choke, mixer])
    with pytest.raises(DomainValidationException) as exc_info:
        recirculation_loop_factory(inner_process=process_system)

    assert str(exc_info.value) == snapshot("Recirculation loop cannot contain splitters or mixers")
