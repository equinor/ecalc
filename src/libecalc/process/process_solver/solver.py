from __future__ import annotations

import abc
import dataclasses
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Self, TypeVar

from libecalc.domain.process.compressor.core.exceptions import CompressorThermodynamicCalculationError
from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_error import (
    CompressorStonewallError,
    CompressorSurgeError,
    InsufficientInletPressureError,
    LiquidAtInletError,
    OfftakeExceedsInletError,
    ProcessError,
)
from libecalc.process.process_pipeline.process_pipeline import ProcessPipelineId
from libecalc.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.process.process_solver.configuration import (
    Configuration,
    ConfigurationHandlerId,
    OperatingConfiguration,
    merge_configurations,
)
from libecalc.process.process_solver.search_strategies import DidNotConvergeError

TConfiguration = TypeVar("TConfiguration", covariant=True)


class SolverFailure:
    """Typed cause for an unsuccessful ``Solution``.

    Subclasses carry the data relevant to a specific failure mode (e.g. above stonewall,
    below surge, target pressure unreachable). Consumers should branch on subclass with
    ``isinstance`` or ``match`` rather than inspecting flag fields.
    """


@dataclass
class CompressorStonewallFailure(SolverFailure):
    source_id: ProcessUnitId
    actual_rate_m3_per_hour: float | None = None
    maximum_rate_m3_per_hour: float | None = None

    @classmethod
    def from_error(cls, e: CompressorStonewallError) -> Self:
        return cls(
            source_id=e.process_unit_id,
            actual_rate_m3_per_hour=e.actual_rate,
            maximum_rate_m3_per_hour=e.boundary_rate,
        )


@dataclass
class CompressorSurgeFailure(SolverFailure):
    source_id: ProcessUnitId
    actual_rate_m3_per_hour: float | None = None
    minimum_rate_m3_per_hour: float | None = None

    @classmethod
    def from_error(cls, e: CompressorSurgeError) -> Self:
        return cls(
            source_id=e.process_unit_id,
            actual_rate_m3_per_hour=e.actual_rate,
            minimum_rate_m3_per_hour=e.boundary_rate,
        )


@dataclass
class ThermodynamicCalculationFailure(SolverFailure):
    reason: str = ""


@dataclass
class ConvergenceFailure(SolverFailure):
    reason: str = ""
    source_id: ProcessPipelineId | None = None
    lower_bound: float | None = None
    upper_bound: float | None = None
    tolerance: float | None = None
    iterations: int | None = None

    @classmethod
    def from_error(cls, e: DidNotConvergeError, source_id: ProcessPipelineId | None = None) -> Self:
        return cls(
            reason=str(e),
            source_id=source_id,
            lower_bound=e.lower_bound,
            upper_bound=e.upper_bound,
            tolerance=e.tolerance,
            iterations=e.iterations,
        )


@dataclass
class LiquidAtInletFailure(SolverFailure):
    process_unit_id: ProcessUnitId | None = None
    vapor_fraction: float | None = None


@dataclass
class InsufficientInletPressureFailure(SolverFailure):
    process_unit_id: ProcessUnitId | None = None
    inlet_pressure_bara: float | None = None
    required_delta_pressure_bara: float | None = None


@dataclass
class OfftakeExceedsInletFailure(SolverFailure):
    process_unit_id: ProcessUnitId | None = None
    available_rate: float | None = None
    offtake_rate: float | None = None


@dataclass
class ProcessFailure(SolverFailure):
    """Catch-all for ProcessError subclasses not yet given a specific failure type."""

    reason: str = ""


def process_error_to_failure(e: ProcessError) -> SolverFailure:
    """Map a ProcessError to the appropriate typed SolverFailure."""
    if isinstance(e, LiquidAtInletError):
        return LiquidAtInletFailure(process_unit_id=e.process_unit_id, vapor_fraction=e.vapor_fraction)
    if isinstance(e, OfftakeExceedsInletError):
        return OfftakeExceedsInletFailure(
            process_unit_id=e.process_unit_id, available_rate=e.available_rate, offtake_rate=e.offtake_rate
        )
    if isinstance(e, InsufficientInletPressureError):
        return InsufficientInletPressureFailure(
            process_unit_id=e.process_unit_id,
            inlet_pressure_bara=e.inlet_pressure_bara,
            required_delta_pressure_bara=e.required_delta_pressure_bara,
        )
    if isinstance(e, CompressorThermodynamicCalculationError):
        return ThermodynamicCalculationFailure(reason=str(e))
    if isinstance(e, CompressorStonewallError):
        return CompressorStonewallFailure.from_error(e)
    if isinstance(e, CompressorSurgeError):
        return CompressorSurgeFailure.from_error(e)
    return ProcessFailure(reason=str(e))


class TargetDirection(Enum):
    """Which side of the target pressure the achievable boundary lies on."""

    MAX_BELOW_TARGET = "max_below_target"
    MIN_ABOVE_TARGET = "min_above_target"


@dataclass
class TargetPressureUnreachableFailure(SolverFailure):
    achievable_pressure_bara: float
    target_pressure_bara: float
    direction: TargetDirection
    source_id: ProcessPipelineId | None = None  # TODO: Replace with failing process unit!

    def with_source_id(self, source_id: ProcessPipelineId) -> Self:
        return dataclasses.replace(self, source_id=source_id)


@dataclass(frozen=True)
class Solution[TConfiguration]:
    configuration: TConfiguration
    failure: SolverFailure | None = field(default=None)

    @property
    def success(self) -> bool:
        return self.failure is None

    @classmethod
    def from_stonewall[T](cls, e: CompressorStonewallError, configuration: T) -> Solution[T]:
        """Build an unsuccessful Solution carrying a CompressorStonewallFailure."""
        return Solution(configuration=configuration, failure=CompressorStonewallFailure.from_error(e))

    @classmethod
    def from_surge[T](cls, e: CompressorSurgeError, configuration: T) -> Solution[T]:
        """Build an unsuccessful Solution carrying a CompressorSurgeFailure."""
        return Solution(configuration=configuration, failure=CompressorSurgeFailure.from_error(e))

    @classmethod
    def target_pressure_unreachable[T](
        cls,
        configuration: T,
        achievable_pressure_bara: float,
        target_pressure_bara: float,
        direction: TargetDirection,
        source_id: ProcessPipelineId | None = None,
    ) -> Solution[T]:
        """Build an unsuccessful Solution carrying a TargetPressureUnreachableFailure."""
        return Solution(
            configuration=configuration,
            failure=TargetPressureUnreachableFailure(
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
        """Combine two solutions as a strict sequential aggregation.

        If self has already failed, returns self unchanged: once a segment in the
        pipeline fails, subsequent segments cannot meaningfully extend it, and the
        failure must keep referring to the configurations it was generated from.

        Otherwise both stages must succeed for the combined solution to succeed;
        any failure carried by other becomes the combined failure. Configurations
        are merged with later entries winning per handler.
        """
        if not self.success:
            return self
        return Solution(
            configuration=merge_configurations(self.configuration, other.configuration),
            failure=other.failure,
        )


class Solver[TConfiguration](abc.ABC):
    @abc.abstractmethod
    def solve(self, func: Callable[[TConfiguration], FluidStream]) -> Solution[TConfiguration]: ...
