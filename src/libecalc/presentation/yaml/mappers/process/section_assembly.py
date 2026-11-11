from libecalc.common.ddd import value_object
from libecalc.ecalc_model.process.configuration_handlers import (
    TimeSeriesChokeConfigurationHandler,
    TimeSeriesConfigurationHandler,
    TimeSeriesRecirculationLoopConfigurationHandler,
)
from libecalc.ecalc_model.process.process_units import (
    TimeSeriesChokeProcessUnit,
    TimeSeriesCompressorProcessUnit,
    TimeSeriesDirectMixerProcessUnit,
    TimeSeriesDirectSplitterProcessUnit,
    TimeSeriesProcessUnit,
)
from libecalc.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeType
from libecalc.process.process_solver.pressure_control.pressure_control_strategy import PressureControlType


@value_object
class AssembledSection:
    process_units: list[TimeSeriesProcessUnit]
    configuration_handlers: list[TimeSeriesConfigurationHandler]


def recirculation_loop(
    process_units: list[TimeSeriesProcessUnit],
) -> tuple[TimeSeriesRecirculationLoopConfigurationHandler, list[TimeSeriesProcessUnit]]:
    mixer, splitter = TimeSeriesDirectMixerProcessUnit(), TimeSeriesDirectSplitterProcessUnit()
    loop = TimeSeriesRecirculationLoopConfigurationHandler(
        mixer_process_unit_id=mixer.get_id(), splitter_process_unit_id=splitter.get_id()
    )
    return loop, [mixer, *process_units, splitter]


def individual_recirculation_loops(
    process_units: list[TimeSeriesProcessUnit],
) -> tuple[list[TimeSeriesRecirculationLoopConfigurationHandler], list[TimeSeriesProcessUnit]]:
    """Wrap each compressor, and only the compressor, in its own recirculation loop.

    Recirculation is sized from the compressor inlet stream, so it is added directly in front of
    the compressor. Upstream units (e.g. a LiquidRemover) would otherwise alter the recirculated
    mass. The recycled gas is scrubbed discharge gas, so this is equivalent to returning it
    upstream of the stage cooler and scrubber as long as these are independent of mass rate.
    """
    solver_units: list[TimeSeriesProcessUnit] = []
    loops: list[TimeSeriesRecirculationLoopConfigurationHandler] = []
    for unit in process_units:
        if isinstance(unit, TimeSeriesCompressorProcessUnit):
            loop, assembled = recirculation_loop([unit])
            loops.append(loop)
            solver_units.extend(assembled)
        else:
            solver_units.append(unit)
    return loops, solver_units


def assemble_process_section(
    process_units: list[TimeSeriesProcessUnit],
    anti_surge: AntiSurgeType,
    pressure_control: PressureControlType,
) -> AssembledSection:
    """Assemble validated section process units into solver-ready process units and configuration handlers."""
    handlers: list[TimeSeriesConfigurationHandler] = []

    if anti_surge == AntiSurgeType.COMMON_ASV:
        loop, solver_units = recirculation_loop(process_units)
        handlers.append(loop)
    else:
        loops, solver_units = individual_recirculation_loops(process_units)
        handlers.extend(loops)

    if pressure_control in ("UPSTREAM_CHOKE", "DOWNSTREAM_CHOKE"):
        choke = TimeSeriesChokeProcessUnit()
        handlers.append(TimeSeriesChokeConfigurationHandler(choke_process_unit_id=choke.get_id()))
        if pressure_control == "UPSTREAM_CHOKE":
            solver_units = [choke, *solver_units]
        else:
            solver_units = [*solver_units, choke]

    return AssembledSection(
        process_units=solver_units,
        configuration_handlers=handlers,
    )
