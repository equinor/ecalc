import abc
from collections.abc import Callable

from libecalc.domain.process.compressor.core.train.utils.common import EPSILON
from libecalc.domain.process.entities.process_units.recirculation_loop import RecirculationLoop
from libecalc.domain.process.entities.shaft import Shaft
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.search_strategies import BinarySearchStrategy, ScipyRootFindingStrategy
from libecalc.domain.process.process_solver.solver import Solution
from libecalc.domain.process.process_solver.solvers.recirculation_solver import (
    RecirculationConfiguration,
    RecirculationSolver,
)
from libecalc.domain.process.process_solver.solvers.speed_solver import SpeedConfiguration, SpeedSolver
from libecalc.domain.process.process_system.process_error import RateTooLowError
from libecalc.domain.process.process_system.process_system import ProcessSystem
from libecalc.domain.process.process_system.process_unit import ProcessUnit
from libecalc.domain.process.value_objects.fluid_stream import FluidService, FluidStream


class CompressorStageProcessUnit(ProcessUnit):
    @abc.abstractmethod
    def get_speed_boundary(self) -> Boundary: ...

    @abc.abstractmethod
    def get_maximum_standard_rate(self, inlet_stream: FluidStream) -> float:
        """
        Maximum standard rate ignoring speed
        """
        ...


class CommonASVSolver:
    def __init__(
        self,
        shaft: Shaft,
        compressors: list[CompressorStageProcessUnit],
        fluid_service: FluidService,
    ) -> None:
        self._shaft = shaft
        self._compressors = compressors
        self._fluid_service = fluid_service
        self._root_finding_strategy = ScipyRootFindingStrategy()
        self._recirculation_loop = RecirculationLoop(
            inner_process=ProcessSystem(
                process_units=self._compressors,
            ),
            fluid_service=self._fluid_service,
        )

    def get_recirculation_loop(self) -> RecirculationLoop:
        return self._recirculation_loop

    def get_initial_speed_boundary(self) -> Boundary:
        speed_boundaries = [compressor.get_speed_boundary() for compressor in self._compressors]
        max_speed = max(speed_boundary.max for speed_boundary in speed_boundaries)
        min_speed = min(speed_boundary.min for speed_boundary in speed_boundaries)
        return Boundary(
            min=min_speed,
            max=max_speed,
        )

    def get_maximum_recirculation_rate(self, inlet_stream: FluidStream) -> float:
        first_compressor = self._compressors[0]
        max_rate = first_compressor.get_maximum_standard_rate(inlet_stream=inlet_stream)
        return max(0.0, max_rate - inlet_stream.standard_rate_sm3_per_day)

    def get_initial_recirculation_rate_boundary(
        self, inlet_stream: FluidStream, minimum_recirculation_rate: float = EPSILON
    ) -> Boundary:
        return Boundary(
            min=minimum_recirculation_rate,
            max=self.get_maximum_recirculation_rate(inlet_stream=inlet_stream) * (1 - EPSILON),
        )

    def get_recirculation_solver(
        self,
        boundary: Boundary,
        target_pressure: FloatConstraint | None = None,
    ) -> RecirculationSolver:
        return RecirculationSolver(
            root_finding_strategy=self._root_finding_strategy,
            search_strategy=BinarySearchStrategy(tolerance=10e-3),
            recirculation_rate_boundary=boundary,
            target_pressure=target_pressure,
        )

    def get_recirculation_func(self, inlet_stream: FluidStream) -> Callable[[RecirculationConfiguration], FluidStream]:
        def recirculation_func(configuration: RecirculationConfiguration) -> FluidStream:
            self._recirculation_loop.set_recirculation_rate(configuration.recirculation_rate)
            return self._recirculation_loop.propagate_stream(inlet_stream=inlet_stream)

        return recirculation_func

    def find_common_asv_solution(
        self, pressure_constraint: FloatConstraint, inlet_stream: FluidStream
    ) -> tuple[Solution[SpeedConfiguration], Solution[RecirculationConfiguration]]:
        speed_solver = SpeedSolver(
            search_strategy=BinarySearchStrategy(),
            root_finding_strategy=self._root_finding_strategy,
            boundary=self.get_initial_speed_boundary(),
            target_pressure=pressure_constraint.value,
        )
        recirculation_solver_to_capacity = self.get_recirculation_solver(
            boundary=self.get_initial_recirculation_rate_boundary(inlet_stream=inlet_stream)
        )
        recirculation_func = self.get_recirculation_func(inlet_stream=inlet_stream)

        def speed_func(configuration: SpeedConfiguration) -> FluidStream:
            try:
                self._shaft.set_speed(configuration.speed)
                self._recirculation_loop.set_recirculation_rate(0)
                return self._recirculation_loop.propagate_stream(inlet_stream=inlet_stream)
            except RateTooLowError:
                solution = recirculation_solver_to_capacity.solve(recirculation_func)
                self._recirculation_loop.set_recirculation_rate(solution.configuration.recirculation_rate)
                return self._recirculation_loop.propagate_stream(inlet_stream=inlet_stream)

        speed_solution = speed_solver.solve(speed_func)
        self._shaft.set_speed(speed_solution.configuration.speed)
        recirculation_solver_with_target_pressure = self.get_recirculation_solver(
            boundary=self.get_initial_recirculation_rate_boundary(
                inlet_stream=inlet_stream,
            ),
            target_pressure=pressure_constraint,
        )
        recirculation_solution = recirculation_solver_with_target_pressure.solve(recirculation_func)
        # Return solution with all configurations
        return speed_solution, recirculation_solution
