import abc
from collections.abc import Callable

from libecalc.domain.process.compressor.core.train.utils.common import EPSILON
from libecalc.domain.process.compressor.core.train.utils.numeric_methods import find_root
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
        Maximum standard rate at current speed
        """
        ...

    @abc.abstractmethod
    def get_minimum_standard_rate(self, inlet_stream: FluidStream) -> float:
        """
        Minimum standard rate at current speed
        """
        ...


class ASVSolver:
    """
    Base class for solving ASV (Anti-Surge Valve) problems.

    Attributes:
        _shaft (Shaft): The shaft associated with the compressors.
        _compressors (list[CompressorStageProcessUnit]): List of compressor stage process units.
        _fluid_service (FluidService): The fluid service used in the process.
        _root_finding_strategy (ScipyRootFindingStrategy): Strategy for root finding.
    """

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

    def get_initial_speed_boundary(self) -> Boundary:
        """
        Retrieve the initial speed boundary for the compressors.

        Returns:
            Boundary: The initial speed boundary.
        """
        speed_boundaries = [compressor.get_speed_boundary() for compressor in self._compressors]
        max_speed = max(speed_boundary.max for speed_boundary in speed_boundaries)
        min_speed = min(speed_boundary.min for speed_boundary in speed_boundaries)
        return Boundary(
            min=min_speed,
            max=max_speed,
        )

    def get_maximum_recirculation_rate_for_compressor(
        self, compressor: CompressorStageProcessUnit, inlet_stream: FluidStream
    ) -> float:
        """
        Calculate the maximum recirculation rate for a given compressor and inlet stream.

        Args:
            compressor (CompressorStageProcessUnit): The compressor stage process unit.
            inlet_stream (FluidStream): The inlet fluid stream.

        Returns:
            float: The maximum recirculation rate.
        """
        max_rate = compressor.get_maximum_standard_rate(inlet_stream=inlet_stream) * (1 - EPSILON)
        return max(0.0, max_rate - inlet_stream.standard_rate_sm3_per_day)

    def get_minimum_recirculation_rate_for_compressor(
        self, compressor: CompressorStageProcessUnit, inlet_stream: FluidStream
    ) -> float:
        """
        Calculate the minimum recirculation rate for a given compressor and inlet stream to bring it inside capacity

        Args:
            compressor (CompressorStageProcessUnit): The compressor stage process unit.
            inlet_stream (FluidStream): The inlet fluid stream.

        Returns:
            float: The maximum recirculation rate.
        """
        min_rate = compressor.get_minimum_standard_rate(inlet_stream=inlet_stream) * (1 + EPSILON)
        return max(0.0, min_rate - inlet_stream.standard_rate_sm3_per_day)

    def get_recirculation_rate_boundary_for_compressor(
        self, compressor: CompressorStageProcessUnit, inlet_stream: FluidStream
    ) -> Boundary:
        """
        Get the recirculation rate boundary for a specific compressor.

        Args:
            compressor (CompressorStageProcessUnit): The compressor stage process unit.
            inlet_stream (FluidStream): The inlet fluid stream.

        Returns:
            Boundary: The recirculation rate boundary.
        """
        return Boundary(
            min=self.get_minimum_recirculation_rate_for_compressor(compressor=compressor, inlet_stream=inlet_stream),
            max=self.get_maximum_recirculation_rate_for_compressor(compressor=compressor, inlet_stream=inlet_stream),
        )

    def get_initial_recirculation_rate_boundary(
        self, inlet_stream: FluidStream, minimum_recirculation_rate: float = EPSILON
    ) -> Boundary:
        return Boundary(
            min=minimum_recirculation_rate,
            max=self.get_maximum_recirculation_rate_for_compressor(
                compressor=self._compressors[0], inlet_stream=inlet_stream
            ),
        )

    def get_recirculation_solver(
        self,
        boundary: Boundary,
        target_pressure: FloatConstraint | None = None,
    ) -> RecirculationSolver:
        """
        Create a recirculation solver for the given boundary and target pressure.

        Args:
            boundary (Boundary): The recirculation rate boundary.
            target_pressure (FloatConstraint | None): The target pressure constraint. Defaults to None.

        Returns:
            RecirculationSolver: The recirculation solver.
        """
        return RecirculationSolver(
            root_finding_strategy=self._root_finding_strategy,
            search_strategy=BinarySearchStrategy(tolerance=10e-3),
            recirculation_rate_boundary=boundary,
            target_pressure=target_pressure,
        )


class IndividualASVRateSolver(ASVSolver):
    def __init__(
        self,
        shaft: Shaft,
        compressors: list[CompressorStageProcessUnit],
        fluid_service: FluidService,
    ) -> None:
        super().__init__(shaft=shaft, compressors=compressors, fluid_service=fluid_service)
        self._recirculation_loops = [
            RecirculationLoop(
                inner_process=ProcessSystem(
                    process_units=[compressor],
                ),
                fluid_service=self._fluid_service,
            )
            for compressor in self._compressors
        ]

    def get_recirculation_loops(self) -> list[RecirculationLoop]:
        return self._recirculation_loops

    def get_recirculation_func(
        self, recirculation_loop: RecirculationLoop, inlet_stream: FluidStream
    ) -> Callable[[RecirculationConfiguration], FluidStream]:
        def recirculation_func(configuration: RecirculationConfiguration) -> FluidStream:
            recirculation_loop.set_recirculation_rate(configuration.recirculation_rate)
            return recirculation_loop.propagate_stream(inlet_stream=inlet_stream)

        return recirculation_func

    def propagate_through_compressors_with_recirculation(self, inlet_stream: FluidStream) -> FluidStream:
        current_stream = inlet_stream
        for recirculation_loop in self._recirculation_loops:
            current_stream = recirculation_loop.propagate_stream(inlet_stream=current_stream)
        return current_stream

    @staticmethod
    def _get_compressor_stage_from_recirculation_loop(
        recirculation_loop: RecirculationLoop,
    ) -> CompressorStageProcessUnit:
        """
        Extracts the CompressorStageProcessUnit from a RecirculationLoop's inner_process.

        Args:
            recirculation_loop (RecirculationLoop): The recirculation loop to extract from.

        Returns:
            CompressorStageProcessUnit: The compressor stage process unit.

        Raises:
            TypeError: If the inner process does not contain exactly one CompressorStageProcessUnit.
        """
        inner_process = recirculation_loop.get_inner_process()
        units = inner_process.get_process_units()
        if not isinstance(units, list) or len(units) != 1:
            raise TypeError("inner_process must contain exactly one process unit")
        unit = units[0]
        if not isinstance(unit, CompressorStageProcessUnit):
            raise TypeError("process unit is not a CompressorStageProcessUnit")
        return unit

    def find_individual_asv_rate_solution(
        self,
        pressure_constraint: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> tuple[Solution[SpeedConfiguration], list[Solution[RecirculationConfiguration]]]:
        speed_solver = SpeedSolver(
            search_strategy=BinarySearchStrategy(),
            root_finding_strategy=self._root_finding_strategy,
            boundary=self.get_initial_speed_boundary(),
            target_pressure=pressure_constraint.value,
        )

        def speed_func(configuration: SpeedConfiguration) -> FluidStream:
            try:
                # set speed on the shaft
                self._shaft.set_speed(configuration.speed)
                # set all recirculation rates to 0 to check if we find a speed solution
                for recirculation_loop in self._recirculation_loops:
                    recirculation_loop.set_recirculation_rate(0)
                return self.propagate_through_compressors_with_recirculation(inlet_stream=inlet_stream)
            except RateTooLowError:
                # one or more of the compressors are below their minimum rate.
                # We want to find the recirculation rate for each compressor that brings the system inside of capacity
                current_stream = inlet_stream
                for recirculation_loop in self._recirculation_loops:
                    compressor = self._get_compressor_stage_from_recirculation_loop(recirculation_loop)
                    rate_needed_to_reach_minimum_rate = self.get_minimum_recirculation_rate_for_compressor(
                        compressor=compressor,
                        inlet_stream=current_stream,
                    )
                    if rate_needed_to_reach_minimum_rate > 0:
                        recirculation_loop.set_recirculation_rate(rate_needed_to_reach_minimum_rate)

                    current_stream = recirculation_loop.propagate_stream(inlet_stream=current_stream)

                return self.propagate_through_compressors_with_recirculation(inlet_stream=inlet_stream)

        speed_solution = speed_solver.solve(speed_func)
        self._shaft.set_speed(speed_solution.configuration.speed)
        if speed_solution.success:
            return speed_solution, [
                Solution(
                    success=True,
                    configuration=RecirculationConfiguration(
                        recirculation_rate=recirculation_loop.get_recirculation_rate()
                    ),
                )
                for recirculation_loop in self._recirculation_loops
            ]
        else:
            # Is the speed at maximum speed? If so no solution can be found - pressure is too high even at maximum speed
            # Is the speed at minimum speed? we can try to use the recirculation loops to lower the pressure to meet the constraint
            if speed_solution.configuration.speed >= self.get_initial_speed_boundary().max:
                return speed_solution, [
                    Solution(success=False, configuration=RecirculationConfiguration(recirculation_rate=0))
                ] * len(self._recirculation_loops)
            else:
                # we are at minimum speed, we can try to recirculate to capacity to see if we can find a solution that way
                # first try maximum recirculation for each compressor to see if we can meet the pressure constraint that way. If not, there is no solution
                current_stream = inlet_stream
                for recirculation_loop in self._recirculation_loops:
                    compressor = self._get_compressor_stage_from_recirculation_loop(recirculation_loop)
                    recirculation_loop.set_recirculation_rate(
                        self.get_maximum_recirculation_rate_for_compressor(
                            compressor=compressor,
                            inlet_stream=current_stream,
                        )
                    )
                    current_stream = recirculation_loop.propagate_stream(inlet_stream=current_stream)

                if current_stream.pressure_bara < pressure_constraint.value:
                    # we can find solution
                    # implementing what we have today. we find the distance from inlet_stream.rate and the maximum rate
                    # for a compressor. We fill with a fraction of this capacity for each compressor (asv_fraction). If this
                    # fraction is not enough to bring the rate to minimum flow, it is magically moved to minimum flow. We
                    # search for the number between 0 and 1 (asv_fraction) that brings us to the pressure constraint.
                    # This is not a perfect solution, but it is a simple solution that does not require a lot of changes to the current code.
                    # It also has the benefit of giving us a recirculation rate for each compressor, which we can use to set the recirculation rates on the loops.

                    def _get_outlet_stream_given_asv_rate_margin(asv_rate_fraction: float) -> FluidStream:
                        current_stream = inlet_stream
                        for recirculation_loop in self._recirculation_loops:
                            compressor = self._get_compressor_stage_from_recirculation_loop(recirculation_loop)
                            recirculation_boundary = self.get_recirculation_rate_boundary_for_compressor(
                                compressor=compressor,
                                inlet_stream=current_stream,
                            )
                            available_capacity = recirculation_boundary.max - inlet_stream.standard_rate_sm3_per_day
                            recirculation_rate = max(asv_rate_fraction * available_capacity, recirculation_boundary.min)
                            recirculation_loop.set_recirculation_rate(recirculation_rate)
                            current_stream = recirculation_loop.propagate_stream(inlet_stream=current_stream)
                        return current_stream

                    def _get_recirculation_rates_given_asv_rate_margin(asv_rate_fraction: float) -> list[float]:
                        recirculation_rates = []
                        current_stream = inlet_stream
                        for recirculation_loop in self._recirculation_loops:
                            compressor = self._get_compressor_stage_from_recirculation_loop(recirculation_loop)
                            recirculation_boundary = self.get_recirculation_rate_boundary_for_compressor(
                                compressor=compressor,
                                inlet_stream=current_stream,
                            )
                            available_capacity = recirculation_boundary.max - inlet_stream.standard_rate_sm3_per_day
                            recirculation_rate = max(asv_rate_fraction * available_capacity, recirculation_boundary.min)
                            recirculation_rates.append(recirculation_rate)
                            recirculation_loop.set_recirculation_rate(recirculation_rate)
                            current_stream = recirculation_loop.propagate_stream(inlet_stream=current_stream)
                        return recirculation_rates

                    result_asv_rate_margin = find_root(
                        lower_bound=0.0,
                        upper_bound=1.0,
                        func=lambda x: _get_outlet_stream_given_asv_rate_margin(asv_rate_fraction=x).pressure_bara
                        - pressure_constraint.value,
                    )
                    recirculation_rates = _get_recirculation_rates_given_asv_rate_margin(result_asv_rate_margin)
                    recirculation_solutions = []
                    for recirculation_rate in recirculation_rates:
                        recirculation_solutions.append(
                            Solution(
                                success=True,
                                configuration=RecirculationConfiguration(
                                    recirculation_rate=recirculation_rate,
                                ),
                            )
                        )
                    return speed_solution, recirculation_solutions
                else:
                    # we can not find solution
                    # what do we return? currently we would return the closest solution, which is at minimum speed and
                    # maximum recirculation.
                    recirculation_solutions = []
                    for recirculation_loop in self._recirculation_loops:
                        recirculation_solutions.append(
                            Solution(
                                success=False,
                                configuration=RecirculationConfiguration(
                                    recirculation_rate=recirculation_loop.get_recirculation_rate()
                                ),
                            )
                        )
                    return speed_solution, recirculation_solutions


class CommonASVSolver(ASVSolver):
    def __init__(
        self,
        shaft: Shaft,
        compressors: list[CompressorStageProcessUnit],
        fluid_service: FluidService,
    ) -> None:
        super().__init__(shaft=shaft, compressors=compressors, fluid_service=fluid_service)
        self._recirculation_loop = RecirculationLoop(
            inner_process=ProcessSystem(
                process_units=self._compressors,
            ),
            fluid_service=self._fluid_service,
        )

    def get_recirculation_loop(self) -> RecirculationLoop:
        return self._recirculation_loop

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
