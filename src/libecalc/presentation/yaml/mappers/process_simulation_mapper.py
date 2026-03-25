from abc import ABC
from dataclasses import dataclass
from typing import Literal

from libecalc.domain.process.entities.process_units.compressor import Compressor
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.outlet_pressure_solver import OutletPressureSolver
from libecalc.domain.process.process_solver.process_runner import ProcessRunner
from libecalc.domain.process.stream_distribution.common_stream_distribution import HasCapacity
from libecalc.domain.process.stream_distribution.priorities_stream_distribution import HasValidity
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


@dataclass
class StreamDistributionItem(HasCapacity, HasValidity, ABC):
    type: Literal["INDIVIDUAL_ASV", "COMMON_ASV"]


@dataclass
class CompressorTrainStreamDistributionItem(StreamDistributionItem):
    """Connects a compressor train's solver to the stream distribution system."""

    solver: OutletPressureSolver
    pressure_constraint: FloatConstraint
    compressors: list[Compressor]
    runner: ProcessRunner

    def is_valid(self, inlet_stream: FluidStream) -> bool:
        """Can the train operate at these inlet conditions?"""
        return self.solver.find_solution(
            pressure_constraint=self.pressure_constraint,
            inlet_stream=inlet_stream,
        ).success

    def get_unhandled_rate(self, inlet_stream: FluidStream) -> float:
        """How much rate (sm³/day) exceeds this train's capacity?"""
        max_rate = self.find_max_feasible_rate(
            pressure_constraint=self.pressure_constraint,
            inlet_stream=inlet_stream,
        )
        return max(0.0, inlet_stream.standard_rate_sm3_per_day - max_rate)

    def find_max_feasible_rate(
        self,
        pressure_constraint: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> float:
        """Find the max standard rate this train can handle.

        Runs find_solution to set correct speed, then checks each
        compressor's chart boundary at its actual inlet conditions.
        """
        if self.solver.find_solution(pressure_constraint, inlet_stream).success:
            return inlet_stream.standard_rate_sm3_per_day

        # Speed is now set. Find the bottleneck. Search for compressor with the lowest max rate
        min_max_rate = float("inf")
        for compressor in self.compressors:
            compressor_inlet = self.runner.run(
                inlet_stream=inlet_stream,
                to_id=compressor.get_id(),
            )
            max_rate = compressor.get_maximum_standard_rate(compressor_inlet)
            min_max_rate = min(min_max_rate, max_rate)

        return max(0.0, min_max_rate)
