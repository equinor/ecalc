from abc import ABC, abstractmethod
from collections.abc import Callable

from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.value_objects.fluid_stream import FluidStream

# Factory for computing recirculation boundary per stage from stage's actual inlet stream
BoundaryFactory = Callable[[int, FluidStream], Boundary]


class PressureControlStrategy(ABC):
    """Strategy for meeting a target outlet pressure at fixed speed.

    Implementations close over the mutable system state at construction time.
    """

    @abstractmethod
    def apply(
        self,
        *,
        target_pressure: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> bool:
        """Adjust the system to meet the target pressure.

        Args:
            target_pressure: Target outlet pressure.
            inlet_stream: The inlet fluid stream.

        Returns:
            True if the target pressure was met, False otherwise.
        """
        ...
