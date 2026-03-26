from libecalc.domain.process.process_solver.feasibility_solver import FeasibilitySolver
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.stream_distribution.common_stream_distribution import HasExcessRate
from libecalc.domain.process.stream_distribution.priorities_stream_distribution import HasValidity
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class StreamDistributionItem(HasExcessRate, HasValidity):
    """Connects a compressor train's solver to the stream distribution system."""

    def __init__(
        self,
        feasibility_solver: FeasibilitySolver,
        target_pressure: FloatConstraint,
    ):
        self._feasibility_solver = feasibility_solver
        self._target_pressure = target_pressure

    def is_valid(self, inlet_stream: FluidStream) -> bool:
        """Can the train operate at these inlet conditions?"""
        return self.get_excess_rate(inlet_stream) == 0.0

    def get_excess_rate(self, inlet_stream: FluidStream) -> float:
        """How much rate (sm³/day) exceeds this train's capacity?"""
        return self._feasibility_solver.get_excess_rate(
            inlet_stream=inlet_stream, target_pressure=self._target_pressure
        )
