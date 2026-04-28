from abc import ABC, abstractmethod
from collections.abc import Sequence

from libecalc.domain.process.process_solver.configuration import Configuration
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.solver import Solution
from libecalc.domain.process.process_solver.solvers.downstream_choke_solver import ChokeConfiguration
from libecalc.domain.process.process_solver.solvers.recirculation_solver import RecirculationConfiguration
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class PressureControlStrategy(ABC):
    """Strategy for meeting a target outlet pressure at fixed speed.

    Implementations close over the mutable system state at construction time.
    """

    @abstractmethod
    def apply(
        self,
        target_pressure: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> Solution[Sequence[Configuration[RecirculationConfiguration | ChokeConfiguration]]]:
        """Adjust the system to meet the target pressure.

        Args:
            target_pressure: Target outlet pressure.
            inlet_stream: The inlet fluid stream.

        Returns:
            Solution containing the manipulations (e.g. recirculation rate, choke ΔP) needed to meet the target pressure.
        """
        ...
