import abc
from collections.abc import Sequence

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_solver.configuration import Configuration
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.process_solver.solver import Solution


class PipelineSolver(abc.ABC):
    """
    So, we have a hierarchy or a collection of different types of solvers for different purposes, or to
    be used in combination with other solvers. We will always need a parent solver to coordinate and orchestrate that,
    so no matter how many solvers or how they are combined, they will hopefully be able to fulfill this signature.
    """

    @abc.abstractmethod
    def find_solution(
        self,
        pressure_targets: Sequence[FloatConstraint],
        inlet_stream: FluidStream,
    ) -> Solution[Sequence[Configuration]]: ...
