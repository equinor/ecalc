import abc
from dataclasses import dataclass

from libecalc.domain.process.process_system.process_system import ProcessSystem
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


@dataclass
class Boundary:
    min: float
    max: float


class StreamConstraint(abc.ABC):
    @abc.abstractmethod
    def check(self, stream: FluidStream) -> bool: ...


class Solver(abc.ABC):
    @abc.abstractmethod
    def solve(self, process_system: ProcessSystem, inlet_stream: FluidStream) -> FluidStream | None: ...


# TODO: Check whether pressure_control fits the solver pattern here or if we need to drop it. 'CompressorTrainCommonShaft.evaluate_with_pressure_control_given_constraints'


class SpeedSolver(Solver):
    def __init__(self, boundary: Boundary, stream_constraint: StreamConstraint):
        self._boundary = boundary
        self._stream_constraint = stream_constraint

    def solve(
        self,
        process_system: ProcessSystem,
        inlet_stream: FluidStream,
    ) -> FluidStream | None:
        maximum_speed = self._boundary.max

        drive_train = process_system.get_drive_train()
        drive_train.set_speed(maximum_speed)
        outlet_stream = process_system.propagate_stream(inlet_stream=inlet_stream)
        if not self._stream_constraint.check(outlet_stream):
            return outlet_stream

        # Check 'CompressorTrainCommonShaft.find_fixed_shaft_speed_given_constraints' for further implementation


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
            if outlet_stream is not None and self._stream_constraint.check(outlet_stream):
                return True

        return False
