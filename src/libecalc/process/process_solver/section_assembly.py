from libecalc.common.ddd import value_object
from libecalc.process.fluid_stream.fluid_service import FluidService
from libecalc.process.process_pipeline.process_unit import ProcessUnit
from libecalc.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeType
from libecalc.process.process_solver.choke_configuration_handler import ChokeConfigurationHandler
from libecalc.process.process_solver.configuration_handler import ConfigurationHandler
from libecalc.process.process_solver.pressure_control.pressure_control_strategy import PressureControlType
from libecalc.process.process_solver.recirculation_loop import RecirculationLoop
from libecalc.process.process_units.choke import Choke
from libecalc.process.process_units.compressor import Compressor
from libecalc.process.process_units.direct_mixer import DirectMixer
from libecalc.process.process_units.direct_splitter import DirectSplitter


@value_object
class AssembledSection:
    """Solver-ready process units + handlers for a given process section."""

    process_units: list[ProcessUnit]
    configuration_handlers: list[ConfigurationHandler]


def recirculation_loop(
    process_units: list[ProcessUnit],
) -> tuple[RecirculationLoop, list[ProcessUnit]]:
    mixer, splitter = DirectMixer(), DirectSplitter()
    loop = RecirculationLoop(mixer=mixer, splitter=splitter)
    return loop, [mixer, *process_units, splitter]


def individual_recirculation_loops(
    process_units: list[ProcessUnit],
) -> tuple[list[RecirculationLoop], list[ProcessUnit]]:
    """Wrap each compressor, and only the compressor, in its own recirculation loop.

    Recirculation is sized from the compressor inlet stream, so it is added directly in front of
    the compressor. Upstream units (e.g. a LiquidRemover) would otherwise alter the recirculated
    mass. The recycled gas is scrubbed discharge gas, so this is equivalent to returning it
    upstream of the stage cooler and scrubber as long as these are independent of mass rate.
    """
    solver_units: list[ProcessUnit] = []
    loops: list[RecirculationLoop] = []
    for unit in process_units:
        if isinstance(unit, Compressor):
            loop, assembled = recirculation_loop([unit])
            loops.append(loop)
            solver_units.extend(assembled)
        else:
            solver_units.append(unit)
    return loops, solver_units


def assemble_process_section(
    process_units: list[ProcessUnit],
    anti_surge: AntiSurgeType,
    pressure_control: PressureControlType,
    fluid_service: FluidService,
) -> AssembledSection:
    """Assemble validated section process units into solver-ready process units and configuration handlers."""
    handlers: list[ConfigurationHandler] = []

    if anti_surge == AntiSurgeType.COMMON_ASV:
        loop, solver_units = recirculation_loop(process_units)
        handlers.append(loop)
    else:
        loops, solver_units = individual_recirculation_loops(process_units)
        handlers.extend(loops)

    if pressure_control in ("UPSTREAM_CHOKE", "DOWNSTREAM_CHOKE"):
        choke = Choke(fluid_service=fluid_service)
        handlers.append(ChokeConfigurationHandler(choke=choke))
        if pressure_control == "UPSTREAM_CHOKE":
            solver_units = [choke, *solver_units]
        else:
            solver_units = [*solver_units, choke]

    return AssembledSection(
        process_units=solver_units,
        configuration_handlers=handlers,
    )
