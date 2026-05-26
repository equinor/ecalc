"""Typed reasons that propagating a stream through a process unit did not
produce an outlet stream.

A process-unit propagation function returns ``FluidStream | PropagationFailure``:
either a stream came out, or here is the structured reason none did.
"""

from __future__ import annotations

import dataclasses
from dataclasses import dataclass
from enum import Enum
from typing import Self

from libecalc.process.process_pipeline.ids import ProcessPipelineId, ProcessUnitId


class PropagationFailure:
    """Base class for the typed reason a propagation did not succeed.

    Subclasses carry the data relevant to a specific outcome (e.g. above
    stonewall, below surge, target pressure unreachable). Consumers should
    branch on subclass with ``isinstance`` or ``match`` rather than
    inspecting flag fields.
    """


@dataclass
class RateTooHigh(PropagationFailure):
    source_id: ProcessUnitId
    actual_rate_m3_per_hour: float | None = None
    maximum_rate_m3_per_hour: float | None = None


@dataclass
class RateTooLow(PropagationFailure):
    source_id: ProcessUnitId
    actual_rate_m3_per_hour: float | None = None
    minimum_rate_m3_per_hour: float | None = None


@dataclass
class InfeasiblePressure(PropagationFailure):
    source_id: ProcessUnitId
    achieved_pressure_bara: float | None = None


class TargetDirection(Enum):
    """Which side of the target pressure the achievable boundary lies on."""

    MAX_BELOW_TARGET = "max_below_target"
    MIN_ABOVE_TARGET = "min_above_target"


@dataclass
class TargetPressureUnreachable(PropagationFailure):
    achievable_pressure_bara: float
    target_pressure_bara: float
    direction: TargetDirection
    source_id: ProcessPipelineId | None = None

    def with_source_id(self, source_id: ProcessPipelineId) -> Self:
        return dataclasses.replace(self, source_id=source_id)


@dataclass
class DidNotConverge(PropagationFailure):
    """Numerical root-finder exhausted its iteration budget without bracketing
    a solution within tolerance.

    This is a *numerical outcome*, not a programmer mistake: the operating
    point may have no solution in the bracket given the requested tolerance.
    Callers should react (tighten tolerance, widen bracket, accept that this
    time-step has no solution), not catch-and-translate an exception.
    """

    iterations: int
    tolerance: float
    lower_bound: float | None = None
    upper_bound: float | None = None
    source_id: ProcessUnitId | ProcessPipelineId | None = None
