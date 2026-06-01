import abc
from collections.abc import Sequence

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_solver.configuration import Configuration, ConfigurationHandlerId, SpeedConfiguration
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.process_solver.solver import Solution, SolverFailure


class SpeedStrategySolution:
    def __init__(
        self,
        speed_solution: Solution[Configuration[SpeedConfiguration]],
        anti_surge_solution: Solution[Sequence[Configuration]] | None = None,
    ):
        self._speed_solution = speed_solution
        self._anti_surge_solution = anti_surge_solution

    def get_speed_configuration(self) -> SpeedConfiguration:
        return self._speed_solution.configuration.value

    def get_anti_surge_solution(self) -> Solution[Sequence[Configuration]] | None:
        return self._anti_surge_solution

    def is_success(self) -> bool:
        if not self._anti_surge_solution:
            return self._speed_solution.success
        return self._speed_solution.success and self._anti_surge_solution.success

    def get_configurations(self) -> Sequence[Configuration]:
        if not self._anti_surge_solution:
            return [self._speed_solution.configuration]
        return [self._speed_solution.configuration, *self._anti_surge_solution.configuration]

    def get_failures(self) -> Sequence[SolverFailure]:
        failures = []
        if self._speed_solution.failure:
            failures.append(self._speed_solution.failure)

        if self._anti_surge_solution and self._anti_surge_solution.failure:
            failures.append(self._anti_surge_solution.failure)

        return failures


class SpeedStrategy(abc.ABC):
    @abc.abstractmethod
    def get_shaft_id(self) -> ConfigurationHandlerId: ...

    @abc.abstractmethod
    def apply(
        self,
        target_pressure: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> SpeedStrategySolution: ...
