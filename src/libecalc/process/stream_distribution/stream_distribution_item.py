from collections.abc import Sequence

from libecalc.common.errors.exceptions import ProgrammingError
from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_solver.feasibility_solver import FeasibilitySolver
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.stream_distribution.common_stream_distribution import HasExcessRate
from libecalc.process.stream_distribution.priorities_stream_distribution import HasValidity


class StreamDistributionItem(HasExcessRate, HasValidity):
    """Connects a compressor train's solver to the stream distribution system."""

    def __init__(
        self,
        feasibility_solver: FeasibilitySolver,
        pressure_targets: Sequence[FloatConstraint] | None = None,
        *,
        target_pressure: FloatConstraint | None = None,
    ):
        # target_pressure is kept for backwards compatibility, use pressure_targets
        if pressure_targets is not None and target_pressure is None:
            targets = tuple(pressure_targets)
        elif pressure_targets is None and target_pressure is not None:
            targets = (target_pressure,)
        else:
            raise ProgrammingError("Exactly one of 'pressure_targets' and 'target_pressure' must be given.")
        self._feasibility_solver = feasibility_solver
        self._pressure_targets: tuple[FloatConstraint, ...] = targets

    def is_valid(self, inlet_stream: FluidStream) -> bool:
        """Can the train operate at these inlet conditions?"""
        return self.get_excess_rate(inlet_stream) == 0.0

    def get_excess_rate(self, inlet_stream: FluidStream) -> float:
        """How much rate (sm³/day) exceeds this train's capacity?"""
        return self._feasibility_solver.get_excess_rate(
            inlet_stream=inlet_stream, pressure_targets=self._pressure_targets
        )
