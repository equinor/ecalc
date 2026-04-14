import abc
from collections.abc import Sequence

from libecalc.domain.process.process_solver.configuration import Configuration
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.solver import Solution
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class ProcessSystemSolver(abc.ABC):
    @abc.abstractmethod
    def find_solution(
        self,
        pressure_constraint: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> Solution[Sequence[Configuration]]: ...
