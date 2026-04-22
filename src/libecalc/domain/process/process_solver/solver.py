import abc
import dataclasses
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Generic, Self, TypeVar

from libecalc.domain.process.process_pipeline.process_pipeline import ProcessPipelineId
from libecalc.domain.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.domain.process.process_solver.configuration import (
    Configuration,
    ConfigurationHandlerId,
    OperatingConfiguration,
    merge_configurations,
)
from libecalc.domain.process.value_objects.fluid_stream import FluidStream

TConfiguration = TypeVar("TConfiguration", covariant=True)


class SolverFailureStatus(str, Enum):
    ABOVE_MAXIMUM_FLOW_RATE = "ABOVE_MAXIMUM_FLOW_RATE"
    BELOW_MINIMUM_FLOW_RATE = "BELOW_MINIMUM_FLOW_RATE"
    MAXIMUM_ACHIEVABLE_DISCHARGE_PRESSURE_BELOW_TARGET = "MAXIMUM_ACHIEVABLE_DISCHARGE_PRESSURE_BELOW_TARGET"
    MINIMUM_ACHIEVABLE_DISCHARGE_PRESSURE_ABOVE_TARGET = "MINIMUM_ACHIEVABLE_DISCHARGE_PRESSURE_ABOVE_TARGET"


@dataclass
class OutsideCapacityEvent:
    status: SolverFailureStatus
    source_id: ProcessUnitId
    actual_value: float | None = None
    boundary_value: float | None = None


@dataclass
class TargetNotAchievableEvent:
    status: SolverFailureStatus
    achievable_value: float
    target_value: float
    source_id: ProcessPipelineId | None = None

    def with_source_id(self, source_id: ProcessPipelineId) -> Self:
        return dataclasses.replace(self, source_id=source_id)


SolverFailureEvent = OutsideCapacityEvent | TargetNotAchievableEvent


@dataclass(frozen=True)
class Solution(Generic[TConfiguration]):
    success: bool
    configuration: TConfiguration
    failure_event: SolverFailureEvent | None = field(default=None)

    def get_configuration(
        self: "Solution[Sequence[Configuration[OperatingConfiguration]]]",
        unit_id: ConfigurationHandlerId,
    ) -> OperatingConfiguration:
        """Find a configuration value by unit ID."""
        for config in self.configuration:
            if config.configuration_handler_id == unit_id:
                return config.value  # type: ignore[return-value]
        raise ValueError(f"No configuration found for unit {unit_id}.")

    def combine(
        self: "Solution[Sequence[Configuration[OperatingConfiguration]]]",
        other: "Solution[Sequence[Configuration[OperatingConfiguration]]]",
    ) -> "Solution[Sequence[Configuration[OperatingConfiguration]]]":
        """Combine two solutions: merge configurations and success flags."""
        return Solution(
            success=self.success and other.success,
            configuration=merge_configurations(self.configuration, other.configuration),
        )


class Solver(abc.ABC, Generic[TConfiguration]):
    @abc.abstractmethod
    def solve(self, func: Callable[[TConfiguration], FluidStream]) -> Solution[TConfiguration]: ...
