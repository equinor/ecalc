from libecalc.process.process_solver.choke_configuration_handler import ChokeConfigurationHandler
from libecalc.process.process_solver.process_pipeline_runner import ProcessPipelineRunner
from libecalc.process.process_solver.recirculation_loop import RecirculationLoop
from libecalc.process.process_units.choke import Choke
from libecalc.process.process_units.direct_mixer import DirectMixer
from libecalc.process.process_units.direct_splitter import DirectSplitter
from libecalc.process.shaft import VariableSpeedShaft


def test_reset_configuration_handler_zeroes_recirculation_loop():
    mixer = DirectMixer()
    splitter = DirectSplitter()
    loop = RecirculationLoop(mixer=mixer, splitter=splitter)
    loop.set_recirculation_rate(5.0)
    runner = ProcessPipelineRunner(configuration_handlers=[loop], units=[mixer, splitter])

    runner.reset_configuration_handler(loop.get_id())

    assert loop.get_recirculation_rate() == 0.0


def test_reset_configuration_handler_zeroes_choke(fluid_service):
    choke = Choke(fluid_service=fluid_service)
    handler = ChokeConfigurationHandler(choke=choke)
    choke.set_pressure_change(3.0)
    runner = ProcessPipelineRunner(configuration_handlers=[handler], units=[choke])

    runner.reset_configuration_handler(handler.get_id())

    assert choke.pressure_change == 0.0


def test_reset_configuration_handler_unsets_shaft_speed():
    shaft = VariableSpeedShaft()
    shaft.set_speed(5000.0)
    assert shaft.speed_is_defined
    runner = ProcessPipelineRunner(configuration_handlers=[shaft], units=[])

    runner.reset_configuration_handler(shaft.get_id())

    assert not shaft.speed_is_defined
