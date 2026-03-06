from collections.abc import Callable

from libecalc.domain.process.compressor.core.train.utils.common import EPSILON
from libecalc.domain.process.entities.process_units.recirculation_loop import RecirculationLoop
from libecalc.domain.process.entities.shaft import Shaft
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.pressure_control.common_asv import CommonASVPressureControlStrategy
from libecalc.domain.process.process_solver.pressure_control.individual_asv import (
    IndividualASVPressureControlStrategy,
    IndividualASVRateControlStrategy,
)
from libecalc.domain.process.process_solver.pressure_control.pressure_control_strategy import PressureControlStrategy
from libecalc.domain.process.process_solver.search_strategies import BinarySearchStrategy, ScipyRootFindingStrategy
from libecalc.domain.process.process_solver.solver import Solution
from libecalc.domain.process.process_solver.solvers.recirculation_solver import (
    RecirculationConfiguration,
    RecirculationSolver,
)
from libecalc.domain.process.process_solver.solvers.speed_solver import SpeedConfiguration, SpeedSolver
from libecalc.domain.process.process_system.compressor_stage_process_unit import CompressorStageProcessUnit
from libecalc.domain.process.process_system.process_error import RateTooLowError
from libecalc.domain.process.process_system.process_system import ProcessSystem
from libecalc.domain.process.process_system.process_unit import create_process_unit_id
from libecalc.domain.process.value_objects.fluid_stream import FluidService, FluidStream


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
        individual_asv_control: bool = True,
        constant_pressure_ratio: bool = False,
    ) -> None:
        self._shaft = shaft
        self._compressors = compressors
        self._fluid_service = fluid_service
        self._root_finding_strategy = ScipyRootFindingStrategy()
        self._individual_asv_control = individual_asv_control
        self._constant_pressure_ratio = constant_pressure_ratio
        self._recirculation_loops = (
            [
                RecirculationLoop(
                    process_unit_id=create_process_unit_id(),
                    inner_process=ProcessSystem(
                        process_units=[compressor],
                    ),
                    fluid_service=self._fluid_service,
                )
                for compressor in self._compressors
            ]
            if individual_asv_control
            else [
                RecirculationLoop(
                    process_unit_id=create_process_unit_id(),
                    inner_process=ProcessSystem(
                        process_units=self._compressors,
                    ),
                    fluid_service=self._fluid_service,
                )
            ]
        )
        # Pressure control strategy — boundary computed lazily in apply()
        if not individual_asv_control:
            self._pressure_control_strategy: PressureControlStrategy = CommonASVPressureControlStrategy(
                recirculation_loop=self._recirculation_loops[0],
                first_compressor=self._compressors[0],
                root_finding_strategy=self._root_finding_strategy,
            )
        elif constant_pressure_ratio:
            self._pressure_control_strategy = IndividualASVPressureControlStrategy(
                recirculation_loops=self._recirculation_loops,
                compressors=self._compressors,
                root_finding_strategy=self._root_finding_strategy,
            )
        else:
            self._pressure_control_strategy = IndividualASVRateControlStrategy(
                recirculation_loops=self._recirculation_loops,
                compressors=self._compressors,
            )

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

    @staticmethod
    def get_maximum_recirculation_rate_for_compressor(
        compressor: CompressorStageProcessUnit, inlet_stream: FluidStream
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

    @staticmethod
    def get_minimum_recirculation_rate_for_compressor(
        compressor: CompressorStageProcessUnit, inlet_stream: FluidStream
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

    @staticmethod
    def get_recirculation_rate_boundary_for_compressor(
        compressor: CompressorStageProcessUnit, inlet_stream: FluidStream
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
            min=ASVSolver.get_minimum_recirculation_rate_for_compressor(
                compressor=compressor, inlet_stream=inlet_stream
            ),
            max=ASVSolver.get_maximum_recirculation_rate_for_compressor(
                compressor=compressor, inlet_stream=inlet_stream
            ),
        )

    def get_initial_recirculation_rate_boundary(
        self,
        inlet_stream: FluidStream,
    ) -> Boundary:
        return self.get_recirculation_rate_boundary_for_compressor(
            compressor=self._compressors[0], inlet_stream=inlet_stream
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

    def get_recirculation_loops(self) -> list[RecirculationLoop]:
        return self._recirculation_loops

    def get_recirculation_loop(self, loop_number: int = 0) -> RecirculationLoop:
        assert loop_number < len(
            self._recirculation_loops
        ), "Loop number exceeds the number of available recirculation loops."
        return self._recirculation_loops[loop_number]

    def propagate_stream_with_minimum_recirculation(self, inlet_stream: FluidStream) -> FluidStream:
        current_stream = inlet_stream
        if self._individual_asv_control:
            for recirculation_loop, compressor in zip(self._recirculation_loops, self._compressors):
                recirculation_loop.set_recirculation_rate(
                    self.get_minimum_recirculation_rate_for_compressor(
                        compressor=compressor,
                        inlet_stream=current_stream,
                    )
                )
                current_stream = recirculation_loop.propagate_stream(inlet_stream=current_stream)
        else:
            # iterate until we are inside capacity, increasing recirculation rate at each iteration
            recirculation_solver_to_capacity = self.get_recirculation_solver(
                boundary=self.get_initial_recirculation_rate_boundary(inlet_stream=current_stream),
            )
            recirculation_func = self.get_recirculation_func(inlet_stream=inlet_stream)
            _ = recirculation_solver_to_capacity.solve(recirculation_func)
            current_stream = self.get_recirculation_loop().propagate_stream(inlet_stream=current_stream)

        return current_stream

    def propagate_stream_with_no_recirculation(self, inlet_stream: FluidStream) -> FluidStream:
        current_stream = inlet_stream
        for recirculation_loop in self._recirculation_loops:
            recirculation_loop.set_recirculation_rate(0)
            current_stream = recirculation_loop.propagate_stream(inlet_stream=current_stream)
        return current_stream

    def get_recirculation_func(
        self, inlet_stream: FluidStream, loop_number: int = 0
    ) -> Callable[[RecirculationConfiguration], FluidStream]:
        def recirculation_func(configuration: RecirculationConfiguration) -> FluidStream:
            self.get_recirculation_loop(loop_number=loop_number).set_recirculation_rate(
                configuration.recirculation_rate
            )
            return self.get_recirculation_loop(loop_number=loop_number).propagate_stream(inlet_stream=inlet_stream)

        return recirculation_func

    def get_recirculation_rate_solutions(self, success: bool = True) -> list[Solution[RecirculationConfiguration]]:
        return [
            Solution(
                success=success,
                configuration=RecirculationConfiguration(
                    recirculation_rate=recirculation_loop.get_recirculation_rate()
                ),
            )
            for recirculation_loop in self._recirculation_loops
        ]

    def _build_asv_result(
        self,
        speed_solution: Solution[SpeedConfiguration],
        success: bool,
    ) -> tuple[Solution[SpeedConfiguration], list[Solution[RecirculationConfiguration]]]:
        return speed_solution, self.get_recirculation_rate_solutions(success=success)

    def _find_speed_solution(
        self,
        pressure_constraint: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> Solution[SpeedConfiguration]:
        speed_solver = SpeedSolver(
            search_strategy=BinarySearchStrategy(),
            root_finding_strategy=self._root_finding_strategy,
            boundary=self.get_initial_speed_boundary(),
            target_pressure=pressure_constraint.value,
        )

        def speed_func(configuration: SpeedConfiguration) -> FluidStream:
            try:
                self._shaft.set_speed(configuration.speed)
                return self.propagate_stream_with_no_recirculation(inlet_stream=inlet_stream)
            except RateTooLowError:
                return self.propagate_stream_with_minimum_recirculation(inlet_stream=inlet_stream)

        speed_solution = speed_solver.solve(speed_func)
        self._shaft.set_speed(speed_solution.configuration.speed)
        return speed_solution

    def find_asv_solution(
        self,
        pressure_constraint: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> tuple[Solution[SpeedConfiguration], list[Solution[RecirculationConfiguration]]]:
        """
        Finds the speed and recirculation rates for each compressor to meet the pressure constraint.
        """
        speed_solution = self._find_speed_solution(pressure_constraint, inlet_stream)

        if speed_solution.success:
            return self._build_asv_result(speed_solution=speed_solution, success=True)

        if speed_solution.configuration.speed >= self.get_initial_speed_boundary().max:
            return self._build_asv_result(speed_solution=speed_solution, success=False)

        success = self._pressure_control_strategy.apply(
            target_pressure=pressure_constraint,
            inlet_stream=inlet_stream,
        )
        return self._build_asv_result(speed_solution=speed_solution, success=success)
