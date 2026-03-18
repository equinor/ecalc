import abc
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Generic, TypeVar

from libecalc.domain.process.entities.shaft.shaft import ShaftId
from libecalc.domain.process.process_solver.solvers.downstream_choke_solver import ChokeConfiguration
from libecalc.domain.process.process_solver.solvers.recirculation_solver import RecirculationConfiguration
from libecalc.domain.process.process_solver.solvers.speed_solver import SpeedConfiguration
from libecalc.domain.process.process_system.process_system import ProcessSystemId
from libecalc.domain.process.process_system.process_unit import ProcessUnitId
from libecalc.domain.process.value_objects.fluid_stream import FluidStream

T_co = TypeVar("T_co", covariant=True)

SimulationUnitId = ProcessUnitId | ProcessSystemId | ShaftId


@dataclass(frozen=True)
class Configuration(Generic[T_co]):
    simulation_unit_id: SimulationUnitId
    value: T_co


class ProcessRunner(abc.ABC):
    @abc.abstractmethod
    def apply_configuration(
        self, configuration: Configuration[ChokeConfiguration | RecirculationConfiguration | SpeedConfiguration]
    ):
        """Apply the given configuration to the process system."""
        ...

    def apply_configurations(
        self,
        configurations: Sequence[Configuration[ChokeConfiguration | RecirculationConfiguration | SpeedConfiguration]],
    ):
        """Apply the given configurations to the process system."""
        for configuration in configurations:
            self.apply_configuration(configuration)

    @abc.abstractmethod
    def run(self, inlet_stream: FluidStream, to_id: SimulationUnitId | None = None) -> FluidStream:
        """
        Simulate the process
        Args:
            inlet_stream: inlet stream to the process.
            to_id: If provided, simulates the process up to, not including, the specified simulation unit id. If None, simulates the entire process.

        Returns: The outlet stream

        """
        ...
