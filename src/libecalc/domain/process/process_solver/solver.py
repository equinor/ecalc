import abc
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Generic, TypeVar

from libecalc.domain.process.process_solver.configuration import Configuration, OperatingConfiguration, SimulationUnitId
from libecalc.domain.process.value_objects.fluid_stream import FluidStream

TConfiguration = TypeVar("TConfiguration")


@dataclass
class Solution(Generic[TConfiguration]):
    success: bool
    configuration: TConfiguration

    def get_configuration(
        self: "Solution[Sequence[Configuration[OperatingConfiguration]]]",
        unit_id: SimulationUnitId,
    ) -> OperatingConfiguration:
        """Find a configuration value by unit ID."""
        for config in self.configuration:
            if config.simulation_unit_id == unit_id:
                return config.value  # type: ignore[return-value]
        raise ValueError(f"No configuration found for unit {unit_id}.")


class Solver(abc.ABC, Generic[TConfiguration]):
    @abc.abstractmethod
    def solve(self, func: Callable[[TConfiguration], FluidStream]) -> Solution[TConfiguration]: ...
