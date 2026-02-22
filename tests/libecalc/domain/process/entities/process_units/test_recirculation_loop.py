import pytest

from libecalc.domain.process.entities.process_units.choke import Choke
from libecalc.domain.process.entities.process_units.liquid_remover import LiquidRemover
from libecalc.domain.process.entities.process_units.mixer.mixer import Mixer
from libecalc.domain.process.entities.process_units.recirculation_loop import RecirculationLoop
from libecalc.domain.process.entities.process_units.splitter.splitter import Splitter
from libecalc.domain.process.process_system.process_system import ProcessSystem


class DummyFluidService:
    pass


def test_recirculation_loop_around_splitter_raises_valueerror():
    process_unit = Splitter(number_of_outputs=2)
    with pytest.raises(ValueError, match="Inner process cannot be a splitter"):
        RecirculationLoop(inner_process=process_unit, fluid_service=DummyFluidService())


def test_recirculation_loop_around_mixer_raises_valueerror():
    process_unit = Mixer(number_of_inputs=2, fluid_service=DummyFluidService())
    with pytest.raises(ValueError, match="Inner process cannot be a mixer"):
        RecirculationLoop(inner_process=process_unit, fluid_service=DummyFluidService())


def test_recirculation_loop_around_process_system_with_multiple_streams_raises_valueerror():
    liquid_remover = LiquidRemover(fluid_service=DummyFluidService())
    choke = Choke(pressure_change=2, fluid_service=DummyFluidService())
    mixer = Mixer(number_of_inputs=2, fluid_service=DummyFluidService())
    process_system = ProcessSystem(process_units=[liquid_remover, choke, mixer])
    with pytest.raises(ValueError, match="Inner process cannot have multiple streams"):
        RecirculationLoop(inner_process=process_system, fluid_service=DummyFluidService())
