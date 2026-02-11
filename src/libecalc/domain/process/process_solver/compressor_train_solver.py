import abc
from typing import Literal, assert_never

from libecalc.domain.process.compressor.core.train.utils.common import EPSILON
from libecalc.domain.process.entities.process_units.recirculation_loop import RecirculationLoop
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.search_strategies import BinarySearchStrategy, ScipyRootFindingStrategy
from libecalc.domain.process.process_solver.solvers.recirculation_solver import (
    RecirculationConfiguration,
    RecirculationSolver,
)
from libecalc.domain.process.process_solver.solvers.speed_solver import SpeedConfiguration, SpeedSolver
from libecalc.domain.process.process_system.process_error import RateTooLowError
from libecalc.domain.process.process_system.process_system import ProcessSystem
from libecalc.domain.process.process_system.process_unit import ProcessUnit
from libecalc.domain.process.value_objects.chart.compressor import CompressorChart
from libecalc.domain.process.value_objects.fluid_stream import FluidService, FluidStream


class CompressorStageProcessUnit(ProcessUnit):
    @abc.abstractmethod
    def get_compressor_chart(self) -> CompressorChart: ...


class CompressorTrainSolver:
    def __init__(
        self,
        compressors: list[CompressorStageProcessUnit],
        pressure_control: Literal["COMMON_ASV", "INDIVIDUAL_ASV", "DOWNSTREAM_CHOKE", "UPSTREAM_CHOKE"],
        fluid_service: FluidService,
    ) -> None:
        self._compressors = compressors
        self._pressure_control = pressure_control
        self._fluid_service = fluid_service
        self._root_finding_strategy = ScipyRootFindingStrategy()

    def get_initial_speed_boundary(self) -> Boundary:
        charts = [compressor.get_compressor_chart() for compressor in self._compressors]
        max_speed = max(chart.maximum_speed for chart in charts)
        min_speed = min(chart.minimum_speed for chart in charts)
        return Boundary(
            min=min_speed,
            max=max_speed,
        )

    def get_initial_recirculation_rate_boundary(self, inlet_stream: FluidStream) -> Boundary:
        first_chart = self._compressors[0].get_compressor_chart()
        max_rate = first_chart.maximum_rate * inlet_stream.density
        return Boundary(
            min=EPSILON,
            max=max_rate * (1 - EPSILON),
        )

    def find_common_asv_solution(self, pressure_constraint: FloatConstraint, inlet_stream: FluidStream):
        process_unit = RecirculationLoop(
            inner_process=ProcessSystem(
                process_units=self._compressors,
            ),
            fluid_service=self._fluid_service,
        )
        speed_solver = SpeedSolver(
            search_strategy=BinarySearchStrategy(),
            root_finding_strategy=self._root_finding_strategy,
            boundary=self.get_initial_speed_boundary(),
            target_pressure=pressure_constraint.value,
        )

        recirculation_solver = RecirculationSolver(
            root_finding_strategy=self._root_finding_strategy,
            search_strategy=BinarySearchStrategy(tolerance=10e-3),
            recirculation_rate_boundary=self.get_initial_recirculation_rate_boundary(inlet_stream=inlet_stream),
            target_pressure=pressure_constraint.value,
        )

        def recirculation_func(configuration: RecirculationConfiguration) -> FluidStream:
            process_unit.set_recirculation_rate(configuration.recirculation_rate)
            return process_unit.propagate_stream(inlet_stream=inlet_stream)

        def speed_func(configuration: SpeedConfiguration) -> FluidStream:
            try:
                return process_unit.propagate_stream(inlet_stream=inlet_stream)
            except RateTooLowError:
                solution = recirculation_solver.solve(recirculation_func)
                process_unit.set_recirculation_rate(solution.configuration.recirculation_rate)
                # TODO: How do we keep configuration from recirc? return solution in func, also containing outlet_stream?
                return process_unit.propagate_stream(inlet_stream=inlet_stream)

        speed_solver.solve(speed_func)

    def find_solution(self, pressure_constraint: FloatConstraint, inlet_stream: FluidStream):
        if self._pressure_control == "COMMON_ASV":
            self.find_common_asv_solution(pressure_constraint, inlet_stream)
        elif self._pressure_control == "INDIVIDUAL_ASV":
            raise NotImplementedError()
        elif self._pressure_control == "DOWNSTREAM_CHOKE":
            raise NotImplementedError()
        elif self._pressure_control == "UPSTREAM_CHOKE":
            raise NotImplementedError()
        else:
            assert_never(self._pressure_control)
