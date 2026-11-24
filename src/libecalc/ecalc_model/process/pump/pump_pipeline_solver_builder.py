from collections.abc import Mapping, Sequence
from itertools import dropwhile

from libecalc.common.errors.exceptions import ProgrammingError
from libecalc.ecalc_model.process.process_units import (
    TimeSeriesChokeProcessUnit,
    TimeSeriesDirectMixerProcessUnit,
    TimeSeriesDirectSplitterProcessUnit,
    TimeSeriesInletProcessUnit,
    TimeSeriesOutletProcessUnit,
    TimeSeriesPressureDropperProcessUnit,
    TimeSeriesProcessUnit,
    TimeSeriesPumpProcessUnit,
)
from libecalc.ecalc_model.process.pump.pump_pipeline import PumpPipeline
from libecalc.ecalc_model.process.pump.pump_problems import validate_pump_problems
from libecalc.ecalc_model.process.pump.pump_simulation import PumpProblem
from libecalc.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.process.process_solver.configuration import ConfigurationHandlerId
from libecalc.process.process_solver.configuration_handler import ConfigurationHandler
from libecalc.process.pump.process_units.liquid_choke import LiquidChoke
from libecalc.process.pump.process_units.liquid_direct_mixer import LiquidDirectMixer
from libecalc.process.pump.process_units.liquid_direct_splitter import LiquidDirectSplitter
from libecalc.process.pump.process_units.liquid_inlet import LiquidInlet
from libecalc.process.pump.process_units.liquid_outlet import LiquidOutlet
from libecalc.process.pump.process_units.liquid_pressure_dropper import LiquidPressureDropper
from libecalc.process.pump.process_units.liquid_process_unit import LiquidProcessUnit
from libecalc.process.pump.pump import Pump
from libecalc.process.pump.pump_solver.liquid_choke_configuration_handler import LiquidChokeConfigurationHandler
from libecalc.process.pump.pump_solver.liquid_process_pipeline_runner import LiquidProcessPipelineRunner
from libecalc.process.pump.pump_solver.liquid_recirculation_loop import LiquidRecirculationLoop
from libecalc.process.pump.pump_solver.pump_pipeline_solver import PumpPipelineSolver
from libecalc.process.pump.pump_solver.pump_problem_solver import PumpProblemSolver

# The id of each recirculation loop of the pump pipeline, by the ids of its mixer and its splitter.
type _RecirculationLoopIds = Mapping[tuple[ProcessUnitId, ProcessUnitId], ConfigurationHandlerId]
type _PumpProblemParts = tuple[Pump, LiquidRecirculationLoop, LiquidChokeConfigurationHandler | None]


def build_pump_pipeline_solver(
    pump_pipeline: PumpPipeline, pump_problems: Sequence[PumpProblem]
) -> tuple[PumpPipelineSolver, LiquidProcessPipelineRunner, Mapping[ProcessUnitId, LiquidPressureDropper]]:
    """The runtime of one pump pipeline and its pump problems, with their ids.

    Returns the solver of the pipeline, the runner that gives the stream into each unit, and the pressure
    droppers by process unit id, whose pressure drop is set per period.

    Every liquid unit has the id of its process unit. A recirculation loop handler has the id of the
    recirculation loop it is built from, and a choke handler has the process unit id of its choke.

    The pipeline starts with an inlet and ends with an outlet. A pump problem covers, in this order, any
    number of pressure droppers, the mixer of a recirculation loop, one pump, the splitter of that loop and,
    when the problem names a choke, that choke. Between the last problem and the outlet there are only
    pressure droppers. Anything else raises ``ProgrammingError``, since the solver of a pump problem evaluates
    its pump for the stream that enters the mixer and for the requested outlet pressure.
    """
    validate_pump_problems(pump_pipeline, pump_problems)
    subject = f"Pump pipeline '{pump_pipeline.get_name()}'"
    units = [_build_unit(process_unit, subject) for process_unit in pump_pipeline.get_process_units()]
    if not isinstance(units[0], LiquidInlet) or not isinstance(units[-1], LiquidOutlet):
        raise ProgrammingError(f"{subject} must start with an inlet and end with an outlet.")

    unit_index_by_id = {unit.get_id(): index for index, unit in enumerate(units)}
    recirculation_loop_ids = {
        (loop.get_mixer_process_unit_id(), loop.get_splitter_process_unit_id()): ConfigurationHandlerId(loop.get_id())
        for loop in pump_pipeline.get_recirculation_loops()
    }
    problem_parts: list[_PumpProblemParts] = []
    start = 1
    for problem in pump_problems:
        end = unit_index_by_id[problem.get_constraint().target_process_unit_id]
        problem_parts.append(_build_problem_parts(subject, problem, units[start : end + 1], recirculation_loop_ids))
        start = end + 1
    if not all(isinstance(unit, LiquidPressureDropper) for unit in units[start:-1]):
        raise ProgrammingError(
            f"{subject} must have only pressure droppers between the target of its last pump problem and its outlet."
        )

    configuration_handlers: list[ConfigurationHandler] = []
    for _, recirculation_loop, choke_configuration_handler in problem_parts:
        configuration_handlers.append(recirculation_loop)
        if choke_configuration_handler is not None:
            configuration_handlers.append(choke_configuration_handler)
    runner = LiquidProcessPipelineRunner(configuration_handlers=configuration_handlers, units=units)
    pipeline_solver = PumpPipelineSolver(
        [
            PumpProblemSolver(
                runner=runner,
                pump=pump,
                recirculation_loop=recirculation_loop,
                choke_configuration_handler=choke_configuration_handler,
            )
            for pump, recirculation_loop, choke_configuration_handler in problem_parts
        ]
    )
    pressure_droppers = {unit.get_id(): unit for unit in units if isinstance(unit, LiquidPressureDropper)}
    return pipeline_solver, runner, pressure_droppers


def _build_unit(process_unit: TimeSeriesProcessUnit, subject: str) -> LiquidProcessUnit:
    match process_unit:
        case TimeSeriesInletProcessUnit():
            return LiquidInlet(process_unit_id=process_unit.get_id())
        case TimeSeriesPressureDropperProcessUnit():
            return LiquidPressureDropper(process_unit_id=process_unit.get_id())
        case TimeSeriesDirectMixerProcessUnit():
            return LiquidDirectMixer(process_unit_id=process_unit.get_id())
        case TimeSeriesPumpProcessUnit():
            return Pump(
                pump_chart=process_unit.pump_chart,
                minimum_flow_rate_m3_per_hour=process_unit.minimum_flow_rate_m3_per_hour,
                process_unit_id=process_unit.get_id(),
            )
        case TimeSeriesDirectSplitterProcessUnit():
            return LiquidDirectSplitter(process_unit_id=process_unit.get_id())
        case TimeSeriesChokeProcessUnit():
            return LiquidChoke(process_unit_id=process_unit.get_id())
        case TimeSeriesOutletProcessUnit():
            return LiquidOutlet(process_unit_id=process_unit.get_id())
        case _:
            raise ProgrammingError(
                f"{subject} has a process unit '{type(process_unit).__name__}', which has no liquid process unit."
            )


def _build_problem_parts(
    subject: str,
    problem: PumpProblem,
    problem_units: Sequence[LiquidProcessUnit],
    recirculation_loop_ids: _RecirculationLoopIds,
) -> _PumpProblemParts:
    """The pump of a pump problem and the handlers of its recirculation loop and its choke."""
    units_from_the_mixer = list(dropwhile(lambda unit: isinstance(unit, LiquidPressureDropper), problem_units))
    choke_id = problem.get_choke_pressure_control_id()

    match units_from_the_mixer:
        case [LiquidDirectMixer() as mixer, Pump() as pump, LiquidDirectSplitter() as splitter] if choke_id is None:
            choke = None
        case [
            LiquidDirectMixer() as mixer,
            Pump() as pump,
            LiquidDirectSplitter() as splitter,
            LiquidChoke() as choke,
        ] if choke.get_id() == choke_id:
            pass
        case _:
            raise _unsupported_problem_units(subject, problem, problem_units)
    recirculation_loop_id = recirculation_loop_ids.get((mixer.get_id(), splitter.get_id()))
    if recirculation_loop_id is None:
        raise _unsupported_problem_units(subject, problem, problem_units)

    return (
        pump,
        LiquidRecirculationLoop(mixer=mixer, splitter=splitter, configuration_handler_id=recirculation_loop_id),
        LiquidChokeConfigurationHandler(choke=choke, configuration_handler_id=ConfigurationHandlerId(choke.get_id()))
        if choke is not None
        else None,
    )


def _unsupported_problem_units(
    subject: str, problem: PumpProblem, problem_units: Sequence[LiquidProcessUnit]
) -> ProgrammingError:
    unit_names = ", ".join(type(unit).__name__ for unit in problem_units)
    return ProgrammingError(
        f"{subject} pump problem '{problem.get_id()}' must cover, in this order, any number of pressure "
        f"droppers, the mixer of a recirculation loop, one pump, the splitter of that loop and, when the problem "
        f"names a choke, that choke. It covers: {unit_names}."
    )
