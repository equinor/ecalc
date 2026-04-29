from abc import ABC, abstractmethod
from collections.abc import Sequence

from libecalc.domain.process.process_solver.configuration import Configuration
from libecalc.domain.process.process_solver.solver import Solution
from libecalc.domain.process.process_solver.solvers.recirculation_solver import RecirculationConfiguration
from libecalc.domain.process.value_objects.stream_protocol import StreamWithPressure


class AntiSurgeStrategy(ABC):
    """
    Strategy for keeping the train within capacity at the current speed.

    Used during speed search when propagation may fail (e.g. RateTooLowError).
    Works for both compressor anti-surge and pump minimum-flow bypass.
    """

    @abstractmethod
    def apply(self, inlet_stream: StreamWithPressure) -> Solution[Sequence[Configuration[RecirculationConfiguration]]]:
        """Adjust recirculation so the system can be propagated without violating capacity."""
        ...

    @abstractmethod
    def reset(self) -> None:
        """Reset mutable control state (e.g. recirculation rates) to zero."""
        ...
