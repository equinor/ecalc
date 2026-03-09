import abc

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
