import abc

from libecalc.domain.process.compressor.core.train.utils.common import RECIRCULATION_BOUNDARY_TOLERANCE
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_system.process_unit import ProcessUnit
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


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

    def get_recirculation_range(self, inlet_stream: FluidStream) -> Boundary:
        """How much recirculation can be added while staying within compressor capacity.

        Returns:
            Boundary where:
                min = minimum recirculation needed to reach minimum flow
                max = maximum recirculation before exceeding maximum flow
        """
        # Use recirculation tolerance to compensate for floating point rounding in rate conversions
        # (standard rate → mass rate → actual rate → chart evaluation).
        min_rate = self.get_minimum_standard_rate(inlet_stream=inlet_stream) * (1 + RECIRCULATION_BOUNDARY_TOLERANCE)
        max_rate = self.get_maximum_standard_rate(inlet_stream=inlet_stream) * (1 - RECIRCULATION_BOUNDARY_TOLERANCE)
        return Boundary(
            min=max(0.0, min_rate - inlet_stream.standard_rate_sm3_per_day),
            max=max(0.0, max_rate - inlet_stream.standard_rate_sm3_per_day),
        )
