from collections.abc import Sequence
from dataclasses import dataclass

import pytest

from libecalc.process.chart.chart import ChartData
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
from libecalc.testing.pump_test_data import single_speed_pump_chart, variable_speed_pump_chart


@pytest.fixture
def single_speed_chart() -> ChartData:
    return single_speed_pump_chart()


@pytest.fixture
def variable_speed_chart() -> ChartData:
    return variable_speed_pump_chart()


@dataclass(frozen=True)
class PumpProblemUnits:
    """The units and the handlers of one pump problem. A problem without a choke has no choke handler."""

    pressure_dropper: LiquidPressureDropper | None
    mixer: LiquidDirectMixer
    pump: Pump
    splitter: LiquidDirectSplitter
    choke: LiquidChoke | None
    recirculation_loop: LiquidRecirculationLoop
    choke_configuration_handler: LiquidChokeConfigurationHandler | None

    def get_units(self) -> list[LiquidProcessUnit]:
        units = (self.pressure_dropper, self.mixer, self.pump, self.splitter, self.choke)
        return [unit for unit in units if unit is not None]

    def get_configuration_handlers(self) -> list[ConfigurationHandler]:
        handlers = (self.recirculation_loop, self.choke_configuration_handler)
        return [handler for handler in handlers if handler is not None]


@dataclass(frozen=True)
class PumpPipelineRuntime:
    """``problems`` and ``problem_solvers`` are in flow order, one of each per pump."""

    problems: tuple[PumpProblemUnits, ...]
    outlet: LiquidOutlet
    runner: LiquidProcessPipelineRunner
    problem_solvers: tuple[PumpProblemSolver, ...]
    solver: PumpPipelineSolver


def _create_problem_units(
    pump_chart: ChartData, has_choke: bool, upstream_pressure_drop_bara: float | None
) -> PumpProblemUnits:
    mixer = LiquidDirectMixer()
    splitter = LiquidDirectSplitter()
    choke = LiquidChoke() if has_choke else None
    return PumpProblemUnits(
        pressure_dropper=(
            LiquidPressureDropper(pressure_drop_bara=upstream_pressure_drop_bara)
            if upstream_pressure_drop_bara is not None
            else None
        ),
        mixer=mixer,
        pump=Pump(pump_chart=pump_chart),
        splitter=splitter,
        choke=choke,
        recirculation_loop=LiquidRecirculationLoop(mixer=mixer, splitter=splitter),
        choke_configuration_handler=LiquidChokeConfigurationHandler(choke=choke) if choke is not None else None,
    )


@pytest.fixture
def make_pump_pipeline_runtime():
    """Builds the units, the handlers, the runner and the solvers of one pump pipeline, as a consumer does."""

    def create(
        pump_chart: ChartData,
        has_choke: Sequence[bool],
        upstream_pressure_drops_bara: Sequence[float | None] | None = None,
    ) -> PumpPipelineRuntime:
        """One pump per entry of ``has_choke``, in flow order.

        An entry of ``upstream_pressure_drops_bara`` is the pressure drop of a pressure dropper upstream of the
        pump's mixer, or ``None`` for no pressure dropper. No pump has a pressure dropper when it is not given.
        """
        if upstream_pressure_drops_bara is None:
            upstream_pressure_drops_bara = [None] * len(has_choke)
        problems = tuple(
            _create_problem_units(pump_chart, choke, upstream_pressure_drop_bara)
            for choke, upstream_pressure_drop_bara in zip(has_choke, upstream_pressure_drops_bara, strict=True)
        )
        outlet = LiquidOutlet()
        runner = LiquidProcessPipelineRunner(
            configuration_handlers=[
                handler for problem in problems for handler in problem.get_configuration_handlers()
            ],
            units=[LiquidInlet(), *(unit for problem in problems for unit in problem.get_units()), outlet],
        )
        problem_solvers = tuple(
            PumpProblemSolver(
                runner=runner,
                pump=problem.pump,
                recirculation_loop=problem.recirculation_loop,
                choke_configuration_handler=problem.choke_configuration_handler,
            )
            for problem in problems
        )
        return PumpPipelineRuntime(
            problems=problems,
            outlet=outlet,
            runner=runner,
            problem_solvers=problem_solvers,
            solver=PumpPipelineSolver(problem_solvers),
        )

    return create
