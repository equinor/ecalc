from typing import Protocol, TypeVar


class StreamWithPressure(Protocol):
    """Minimal stream interface required by pressure-based solvers.

    Satisfied by both FluidStream and LiquidStream.
    """

    @property
    def pressure_bara(self) -> float: ...


StreamT = TypeVar("StreamT", bound=StreamWithPressure)
