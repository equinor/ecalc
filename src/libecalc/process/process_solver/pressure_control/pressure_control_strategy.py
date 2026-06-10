from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Literal

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_solver.configuration import ChokeConfiguration, Configuration, RecirculationConfiguration
from libecalc.process.process_solver.float_constraint import FloatConstraint
from libecalc.process.process_solver.solver import Solution

PressureControlType = Literal[
    "UPSTREAM_CHOKE",
    "DOWNSTREAM_CHOKE",
    "COMMON_ASV",
    "INDIVIDUAL_ASV_RATE",
    "INDIVIDUAL_ASV_PRESSURE",
]


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

    @abstractmethod
    def reset(self) -> None:
        """Restore any state owned by the strategy to its default/unconfigured value.

        Called before re-evaluating in contexts where stale state from a previous
        evaluation (e.g. a choke ΔP set during a prior solve) would corrupt the
        result.
        """
        ...
