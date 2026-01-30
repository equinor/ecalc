from libecalc.domain.process.process_solver.solver import Solver
from libecalc.domain.process.process_solver.stream_constraint import StreamConstraint
from libecalc.domain.process.process_system.process_system import ProcessSystem
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class ProcessSolver:
    def __init__(
        self,
        inlet_stream: FluidStream,
        process_system: ProcessSystem,
        solvers: list[Solver],
        stream_constraint: StreamConstraint,
    ):
        self._process_system = process_system
        self._inlet_stream = inlet_stream
        self._solvers = solvers
        self._stream_constraint = stream_constraint

    def find_solution(self) -> bool:
        for solver in self._solvers:
            outlet_stream = solver.solve(process_system=self._process_system, inlet_stream=self._inlet_stream)
            if self._stream_constraint.check(outlet_stream):
                return True

        return False
