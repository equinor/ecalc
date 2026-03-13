import abc
from dataclasses import dataclass
from typing import Generic, TypeVar

from libecalc.domain.process.process_solver.solvers.downstream_choke_solver import ChokeConfiguration
from libecalc.domain.process.process_solver.solvers.recirculation_solver import RecirculationConfiguration
from libecalc.domain.process.process_solver.solvers.speed_solver import SpeedConfiguration
from libecalc.domain.process.process_system.process_system import ProcessSystemId
from libecalc.domain.process.process_system.process_unit import ProcessUnitId
from libecalc.domain.process.value_objects.fluid_stream import FluidStream

T = TypeVar("T")

SimulationUnitId = ProcessUnitId | ProcessSystemId


@dataclass
class Configuration(Generic[T]):
    simulation_unit_id: SimulationUnitId
    value: ChokeConfiguration | RecirculationConfiguration | SpeedConfiguration


class ProcessSimulator(abc.ABC):
    @abc.abstractmethod
    def apply_configuration(self, configuration: Configuration):
        """Apply the given configuration to the process system."""
        ...

    @abc.abstractmethod
    def simulate(self, to_id: SimulationUnitId | None = None) -> FluidStream:
        """
        Simulate the process
        Args:
            to_id: If provided, simulates the process up to, not including, the specified simulation unit id. If None, simulates the entire process.

        Returns: The outlet stream

        """
        ...
