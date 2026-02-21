from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Literal

from libecalc.domain.process.compressor.core.train.utils.common import EPSILON
from libecalc.domain.process.entities.process_units.recirculation_loop import RecirculationLoop
from libecalc.domain.process.entities.shaft import Shaft
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.search_strategies import BinarySearchStrategy, ScipyRootFindingStrategy
from libecalc.domain.process.process_solver.solver import Solution
from libecalc.domain.process.process_solver.solvers.recirculation_solver import (
    RecirculationConfiguration,
    RecirculationSolver,
)
from libecalc.domain.process.process_solver.solvers.speed_solver import SpeedConfiguration, SpeedSolver
from libecalc.domain.process.process_system.process_error import ProcessError, RateTooLowError
from libecalc.domain.process.process_system.process_system import ProcessSystem
from libecalc.domain.process.process_system.process_unit import ProcessUnit
from libecalc.domain.process.value_objects.chart.compressor import CompressorChart
from libecalc.domain.process.value_objects.fluid_stream import FluidService, FluidStream

from .float_constraint import FloatConstraint


class CompressorStageProcessUnit(ProcessUnit):
    @abc.abstractmethod
    def get_compressor_chart(self) -> CompressorChart: ...


@dataclass(frozen=True)
class CommonAsvConfiguration:
    """
    Joint configuration for COMMON_ASV. Return both control variables (speed and recirculation_rate)
    since they are interdependent.
    """

    speed: float
    recirculation_rate: float


class CompressorTrainSolver:
    """
    High-level solver for compressor train pressure control strategies.
    """

    def __init__(
        self,
        compressors: list[CompressorStageProcessUnit],
        pressure_control: Literal["COMMON_ASV", "INDIVIDUAL_ASV", "DOWNSTREAM_CHOKE", "UPSTREAM_CHOKE"],
        fluid_service: FluidService,
        shaft: Shaft,
    ) -> None:
        self._compressors = compressors
        self._pressure_control = pressure_control
        self._fluid_service = fluid_service
        self._shaft = shaft
        self._root_finding_strategy = ScipyRootFindingStrategy()

    def get_initial_speed_boundary(self) -> Boundary:
        charts = [compressor.get_compressor_chart() for compressor in self._compressors]
        return Boundary(
            min=min(chart.minimum_speed for chart in charts),
            max=max(chart.maximum_speed for chart in charts),
        )

    def get_initial_recirculation_rate_boundary(self, inlet_stream: FluidStream) -> Boundary:
        """
        RecirculationLoop uses recirculation_rate as EXTRA standard rate [Sm3/day] added at the train inlet.
        Estimate an upper bound from the first stage chart max actual rate (Am3/h) converted to Sm3/day.
        """
        chart = self._compressors[0].get_compressor_chart()

        max_mass_rate_kg_per_hour = float(chart.maximum_rate) * float(inlet_stream.density)

        # Convert chart max actual rate [Am3/h] -> max standard rate [Sm3/day] at inlet conditions.
        max_standard_rate_sm3_per_day = float(
            self._fluid_service.mass_rate_to_standard_rate(
                inlet_stream.fluid_model,
                max_mass_rate_kg_per_hour,
            )
        )

        # Boundary is for additional ("recirculated") standard rate, not total train throughput.
        max_additional = max(0.0, max_standard_rate_sm3_per_day - float(inlet_stream.standard_rate_sm3_per_day))

        return Boundary(
            min=0.0,
            max=max_additional * (1 - EPSILON),
        )

    def find_common_asv_solution(
        self,
        pressure_constraint: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> Solution[CommonAsvConfiguration]:
        """
        Solve COMMON_ASV using a nested strategy (speed outer loop, recirculation inner loop).

        SpeedSolver selects shaft speed to meet the outlet pressure target. For each speed candidate,
        RecirculationSolver increases recirculation only as needed to make the train feasible
        (e.g. handles RateTooLow by increasing recirculated standard rate [Sm3/day]).

        Note:
            Recirculation policy is deterministic per speed evaluation: start with recirculation=0,
            then increase to the minimum feasible recirculation rate if needed.
        """

        # Wrap the full compressor train in a RecirculationLoop so "common ASV" adds/removes
        # one shared recirc rate (in standard rate Sm3/day) at the train inlet/outlet.
        recirculation_loop = RecirculationLoop(
            inner_process=ProcessSystem(process_units=self._compressors),
            fluid_service=self._fluid_service,
        )

        speed_solver = SpeedSolver(
            search_strategy=BinarySearchStrategy(),
            root_finding_strategy=self._root_finding_strategy,
            boundary=self.get_initial_speed_boundary(),
            target_pressure=pressure_constraint.value,
        )

        # Inner solver: find the minimum recirc rate that avoids RateTooLow at the current speed.
        # Note: target_pressure=None => we don't use recirc to meet pressure, only to become feasible.
        recirculation_solver = RecirculationSolver(
            root_finding_strategy=self._root_finding_strategy,
            search_strategy=BinarySearchStrategy(tolerance=10e-3),
            recirculation_rate_boundary=self.get_initial_recirculation_rate_boundary(inlet_stream=inlet_stream),
            target_pressure=None,  # feasibility only; speed controls outlet pressure
        )

        def evaluate_train_at_speed(speed: float) -> tuple[FluidStream, float]:
            """
            Evaluate the compressor train outlet stream at a fixed shaft speed using the COMMON_ASV policy.
            Policy:
              1) Set shaft speed
              2) Try to propagate with recirculation rate = 0
              3) if RateTooLow: find the minimum feasible recirculation and re-evaluate

            Returns:
                tuple[FluidStream, float]: (outlet_stream, recirculation_rate_used), where recirculation_rate_used is the
                    additional recirculation rate [Sm3/day] required to make the train feasible at this speed.
                    A value of 0.0 means no recirculation was needed.
            """

            # 1) Speed candidate from SpeedSolver
            self._shaft.set_speed(speed)

            # 2) Always start with recirculation=0 at the current speed, then only add recirc if RateTooLow occurs.
            #   (Recirculation is used for feasibility only; speed controls outlet pressure.)
            recirculation_loop.set_recirculation_rate(0.0)

            try:
                # Feasible at this speed without any recirculation.
                out = recirculation_loop.propagate_stream(inlet_stream=inlet_stream)
                return out, 0.0
            except RateTooLowError as err:
                # 3) Inner solve: find minimum recirculation that makes the train feasible at this speed
                recirculation_solution = recirculation_solver.solve(evaluate_train_at_recirculation)
                if not recirculation_solution.success:
                    # No feasible recirculation within boundary => treat as infeasible at this speed.
                    raise ProcessError("Unable to find feasible recirculation rate within boundary.") from err

                recirculation_loop.set_recirculation_rate(recirculation_solution.configuration.recirculation_rate)
                out = recirculation_loop.propagate_stream(inlet_stream=inlet_stream)
                return out, recirculation_solution.configuration.recirculation_rate

        def evaluate_train_at_recirculation(configuration: RecirculationConfiguration) -> FluidStream:
            """
            RecirculationSolver function.

            Evaluates the train at the current speed with a candidate recirculation rate (Sm3/day).
            """
            recirculation_loop.set_recirculation_rate(configuration.recirculation_rate)
            return recirculation_loop.propagate_stream(inlet_stream=inlet_stream)

        # SpeedSolver only accepts a function that returns the outlet stream.
        # COMMON_ASV evaluation also needs the recirculation rate used at a given speed (for the final configuration),
        # so we keep the full evaluation in evaluate_train_at_speed(...) and let speed_func return only the stream.
        def speed_func(configuration: SpeedConfiguration) -> FluidStream:
            """SpeedSolver function (returns outlet stream only)."""
            out, _ = evaluate_train_at_speed(configuration.speed)
            return out

        speed_solution = speed_solver.solve(speed_func)

        if not speed_solution.success:
            return Solution(
                success=False,
                configuration=CommonAsvConfiguration(speed=speed_solution.configuration.speed, recirculation_rate=0.0),
            )

        # Re-evaluate at the final speed to capture the recirculation rate used by COMMON_ASV for the returned speed.
        _, recirculation_rate = evaluate_train_at_speed(speed_solution.configuration.speed)

        return Solution(
            success=True,
            configuration=CommonAsvConfiguration(
                speed=speed_solution.configuration.speed,
                recirculation_rate=recirculation_rate,
            ),
        )

    def find_solution(self, pressure_constraint: FloatConstraint, inlet_stream: FluidStream):
        if self._pressure_control == "COMMON_ASV":
            return self.find_common_asv_solution(pressure_constraint, inlet_stream)
        elif self._pressure_control == "INDIVIDUAL_ASV":
            raise NotImplementedError()
        elif self._pressure_control == "DOWNSTREAM_CHOKE":
            raise NotImplementedError()
        elif self._pressure_control == "UPSTREAM_CHOKE":
            raise NotImplementedError()
        else:
            raise ValueError(f"Unknown pressure_control={self._pressure_control!r}")
