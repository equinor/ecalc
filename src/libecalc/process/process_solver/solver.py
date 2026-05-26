from __future__ import annotations

import abc
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import TypeVar

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_pipeline import ProcessPipelineId
from libecalc.process.process_pipeline.propagation_failure import (
    PropagationFailure,
    TargetDirection,
    TargetPressureUnreachable,
)
from libecalc.process.process_solver.configuration import (
    Configuration,
    ConfigurationHandlerId,
    OperatingConfiguration,
    merge_configurations,
)

TConfiguration = TypeVar("TConfiguration", covariant=True)

PropagationCallback = Callable[[TConfiguration], "FluidStream | PropagationFailure"]
"""A function that takes a configuration and returns either an outlet
stream or a structured reason none was produced."""


class InfeasibleDuringSearch(Exception):
    """Carries a PropagationFailure out of a closure invoked by a numeric solver.

    Scipy / binary-search callbacks must return ``float``; they have no channel
    for the typed PropagationFailure values produced by the underlying process
    units. Solver closures raise this at the boundary, and the caller catches
    it to translate back into a failed Solution.
    """

    def __init__(self, failure: PropagationFailure) -> None:
        super().__init__(failure)
        self.failure = failure


@dataclass(frozen=True)
class Solution[TConfiguration]:
    success: bool
    configuration: TConfiguration
    failure: PropagationFailure | None = field(default=None)

    @classmethod
    def failed[T](cls, configuration: T, failure: PropagationFailure) -> Solution[T]:
        """Build an unsuccessful Solution carrying the given PropagationFailure."""
        return Solution(success=False, configuration=configuration, failure=failure)

    @classmethod
    def target_pressure_unreachable[T](
        cls,
        configuration: T,
        achievable_pressure_bara: float,
        target_pressure_bara: float,
        direction: TargetDirection,
        source_id: ProcessPipelineId | None = None,
    ) -> Solution[T]:
        """Build an unsuccessful Solution carrying a TargetPressureUnreachable result."""
        return Solution(
            success=False,
            configuration=configuration,
            failure=TargetPressureUnreachable(
                achievable_pressure_bara=achievable_pressure_bara,
                target_pressure_bara=target_pressure_bara,
                direction=direction,
                source_id=source_id,
            ),
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
    def solve(self, func: PropagationCallback[TConfiguration]) -> Solution[TConfiguration]: ...
