import abc

from libecalc.domain.process.process_system.process_system import ProcessSystem
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class Solver(abc.ABC):
    @abc.abstractmethod
    def solve(self, process_system: ProcessSystem, inlet_stream: FluidStream) -> FluidStream | None: ...
