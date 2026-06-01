from typing import Final

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_solver.boundary import Boundary
from libecalc.process.process_solver.configuration import Configuration, ConfigurationHandlerId, SpeedConfiguration
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.process_solver.process_runner import ProcessRunner
from libecalc.process.process_solver.search_strategies import BinarySearchStrategy, RootFindingStrategy
from libecalc.process.process_solver.solver import Solution
from libecalc.process.process_solver.solvers.speed_solver import SpeedSolver


class SpeedSearch:
    def __init__(
        self,
        runner: ProcessRunner,
        shaft_id: ConfigurationHandlerId,
        speed_boundary: Boundary,
        root_finding_strategy: RootFindingStrategy,
    ) -> None:
        self._runner: Final = runner
        self._shaft_id: Final = shaft_id
        self._speed_boundary: Final = speed_boundary
        self._root_finding_strategy: Final = root_finding_strategy

    def find_speed(
        self,
        target_pressure: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> Solution[SpeedConfiguration]:
        speed_solver = SpeedSolver(
            search_strategy=BinarySearchStrategy(),
            root_finding_strategy=self._root_finding_strategy,
            boundary=self._speed_boundary,
            target_pressure=target_pressure.value,
        )

        def speed_func(configuration: SpeedConfiguration) -> FluidStream:
            self._runner.reset_to(
                configurations=[Configuration(configuration_handler_id=self._shaft_id, value=configuration)],
            )
            return self._runner.run(inlet_stream=inlet_stream)

        return speed_solver.solve(speed_func)
