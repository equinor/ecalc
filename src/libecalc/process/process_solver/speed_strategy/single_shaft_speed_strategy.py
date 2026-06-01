from typing import Final

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_error import RateTooLowError
from libecalc.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeStrategy
from libecalc.process.process_solver.boundary import Boundary
from libecalc.process.process_solver.configuration import Configuration, ConfigurationHandlerId, SpeedConfiguration
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.process_solver.process_runner import ProcessRunner
from libecalc.process.process_solver.search_strategies import BinarySearchStrategy, RootFindingStrategy
from libecalc.process.process_solver.solver import RateTooHighFailure, Solution
from libecalc.process.process_solver.solvers.speed_solver import SpeedSolver
from libecalc.process.process_solver.speed_strategy.speed_strategy import SpeedStrategy, SpeedStrategySolution


class SingleShaftSpeedStrategy(SpeedStrategy):
    def __init__(
        self,
        shaft_id: ConfigurationHandlerId,
        speed_boundary: Boundary,
        root_finding_strategy: RootFindingStrategy,
        runner: ProcessRunner,
        anti_surge_strategy: AntiSurgeStrategy,
    ):
        self._shaft_id: ConfigurationHandlerId = shaft_id
        self._root_finding_strategy: RootFindingStrategy = root_finding_strategy
        self._speed_boundary: Final = speed_boundary
        self._runner: ProcessRunner = runner
        self._anti_surge_strategy: AntiSurgeStrategy = anti_surge_strategy

    def get_shaft_id(self) -> ConfigurationHandlerId:
        return self._shaft_id

    def _get_initial_speed_boundary(self) -> Boundary:
        return self._speed_boundary

    def _find_speed_solution(
        self,
        pressure_constraint: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> Solution[Configuration[SpeedConfiguration]]:
        speed_solver = SpeedSolver(
            search_strategy=BinarySearchStrategy(),
            root_finding_strategy=self._root_finding_strategy,
            boundary=self._get_initial_speed_boundary(),
            target_pressure=pressure_constraint.value,
        )

        def speed_func(configuration: SpeedConfiguration) -> FluidStream:
            self._runner.reset_to(
                configurations=[Configuration(configuration_handler_id=self._shaft_id, value=configuration)],
            )
            try:
                return self._runner.run(inlet_stream=inlet_stream)
            except RateTooLowError:
                solution = self._anti_surge_strategy.apply(inlet_stream=inlet_stream)
                self._runner.apply_configurations(solution.configuration)
                return self._runner.run(inlet_stream=inlet_stream)

        speed_solution = speed_solver.solve(speed_func)

        return Solution(
            configuration=Configuration(configuration_handler_id=self._shaft_id, value=speed_solution.configuration),
            success=speed_solution.success,
            failure=speed_solution.failure,
        )

    def apply(
        self,
        target_pressure: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> SpeedStrategySolution:
        speed_solution = self._find_speed_solution(pressure_constraint=target_pressure, inlet_stream=inlet_stream)

        # Short-circuit: if rate exceeds compressor capacity at all speeds, anti-surge cannot help
        if isinstance(speed_solution.failure, RateTooHighFailure):
            return SpeedStrategySolution(
                speed_solution=speed_solution,
            )

        self._runner.reset_to(configurations=[speed_solution.configuration])
        anti_surge_solution = self._anti_surge_strategy.apply(inlet_stream=inlet_stream)

        return SpeedStrategySolution(
            speed_solution=speed_solution,
            anti_surge_solution=anti_surge_solution,
        )
