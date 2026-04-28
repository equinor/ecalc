from __future__ import annotations

from typing import Protocol, Self, TypeVar


class StreamWithPressure(Protocol):
    """Minimal stream interface required by pressure-based solvers.

    Satisfied by both FluidStream and LiquidStream.
    """

    @property
    def pressure_bara(self) -> float: ...


StreamT = TypeVar("StreamT", bound=StreamWithPressure)


class MixableStream(StreamWithPressure, Protocol):
    """Stream interface required by DirectMixer and DirectSplitter.

    Extends StreamWithPressure with the mass-rate and density attributes needed
    to add/remove a recirculation flow in Sm³/day.
    Satisfied by both FluidStream and LiquidStream.
    """

    @property
    def standard_density(self) -> float: ...

    @property
    def mass_rate_kg_per_h(self) -> float: ...

    def with_mass_rate(self, mass_rate_kg_per_h: float) -> Self: ...
