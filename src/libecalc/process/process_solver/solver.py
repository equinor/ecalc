from __future__ import annotations

import abc
import dataclasses
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Self, TypeVar

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_error import (
    InfeasiblePressureError,
    RateTooHighError,
    RateTooLowError,
)
from libecalc.process.process_pipeline.process_pipeline import ProcessPipelineId
from libecalc.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.process.process_solver.configuration import (
    Configuration,
    ConfigurationHandlerId,
    OperatingConfiguration,
    merge_configurations,
)

TConfiguration = TypeVar("TConfiguration", covariant=True)


class SolverFailure:
    """Typed cause for an unsuccessful ``Solution``.

    Subclasses carry the data relevant to a specific failure mode (e.g. above stonewall,
    below surge, target pressure unreachable). Consumers should branch on subclass with
    ``isinstance`` or ``match`` rather than inspecting flag fields.
    """


@dataclass
class RateTooHighFailure(SolverFailure):
    source_id: ProcessUnitId
    actual_rate_m3_per_hour: float | None = None
    maximum_rate_m3_per_hour: float | None = None

    @classmethod
    def from_error(cls, e: RateTooHighError) -> Self:
        return cls(
            source_id=e.process_unit_id,
            actual_rate_m3_per_hour=e.actual_rate,
            maximum_rate_m3_per_hour=e.boundary_rate,
        )


@dataclass
class RateTooLowFailure(SolverFailure):
    source_id: ProcessUnitId
    actual_rate_m3_per_hour: float | None = None
    minimum_rate_m3_per_hour: float | None = None

    @classmethod
    def from_error(cls, e: RateTooLowError) -> Self:
        return cls(
            source_id=e.process_unit_id,
            actual_rate_m3_per_hour=e.actual_rate,
            minimum_rate_m3_per_hour=e.boundary_rate,
        )


@dataclass
class InfeasiblePressureFailure(SolverFailure):
    source_id: ProcessUnitId
    achieved_pressure_bara: float | None = None

    @classmethod
    def from_error(cls, e: InfeasiblePressureError) -> Self:
        return cls(
            source_id=e.process_unit_id,
            achieved_pressure_bara=e.achieved_pressure_bara,
        )


class TargetDirection(Enum):
    """Which side of the target pressure the achievable boundary lies on."""

    MAX_BELOW_TARGET = "max_below_target"
    MIN_ABOVE_TARGET = "min_above_target"


@dataclass
class TargetPressureUnreachableFailure(SolverFailure):
    achievable_pressure_bara: float
    target_pressure_bara: float
    direction: TargetDirection
    source_id: ProcessPipelineId | None = None

    def with_source_id(self, source_id: ProcessPipelineId) -> Self:
        return dataclasses.replace(self, source_id=source_id)


@dataclass(frozen=True)
class Solution[TConfiguration]:
    success: bool
    configuration: TConfiguration
    failure: SolverFailure | None = field(default=None)

    @classmethod
    def from_infeasible_pressure(
        cls, e: InfeasiblePressureError, configuration: TConfiguration
    ) -> Solution[TConfiguration]:
        """Build an unsuccessful Solution carrying an InfeasiblePressureFailure."""
        return cls(
            success=False,
            configuration=configuration,
            failure=InfeasiblePressureFailure.from_error(e),
        )

    def get_configuration(
        self: Solution[Sequence[Configuration[OperatingConfiguration]]],
        unit_id: ConfigurationHandlerId,
    ) -> OperatingConfiguration:
        """Find a configuration value by unit ID."""
        for config in self.configuration:
            if config.configuration_handler_id == unit_id:
                return config.value  # type: ignore[return-value]
        raise ValueError(f"No configuration found for unit {unit_id}.")

    def combine(
        self: Solution[Sequence[Configuration[OperatingConfiguration]]],
        other: Solution[Sequence[Configuration[OperatingConfiguration]]],
    ) -> Solution[Sequence[Configuration[OperatingConfiguration]]]:
        """Combine two solutions: merge configurations and success flags."""
        return Solution(
            success=self.success and other.success,
            configuration=merge_configurations(self.configuration, other.configuration),
        )


class Solver[TConfiguration](abc.ABC):
    @abc.abstractmethod
    def solve(self, func: Callable[[TConfiguration], FluidStream]) -> Solution[TConfiguration]: ...
