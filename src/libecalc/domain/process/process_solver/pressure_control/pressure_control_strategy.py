from abc import ABC, abstractmethod
from enum import StrEnum

from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.pressure_control.configuration import (
    ConfigurationRunner,
    PressureControlConfiguration,
)
from libecalc.domain.process.process_solver.solver import Solution
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class PressureControlStrategyType(StrEnum):
    NONE = "NONE"
    COMMON_ASV = "COMMON_ASV"
    INDIVIDUAL_ASV_RATE = "INDIVIDUAL_ASV_RATE"
    INDIVIDUAL_ASV_PRESSURE = "INDIVIDUAL_ASV_PRESSURE"
    DOWNSTREAM_CHOKE = "DOWNSTREAM_CHOKE"
    UPSTREAM_CHOKE = "UPSTREAM_CHOKE"


class PressureControlStrategy(ABC):
    """Strategy for meeting a target outlet pressure at fixed speed.

    Adjusts recirculation rates, choke settings, or ASV fractions to bring
    outlet pressure to the target. Assumes capacity has already been
    handled (i.e., the operating point is within compressor chart limits).

    The strategy interacts with the physical system
    only through the ConfigurationRunner.
    """

    @abstractmethod
    def apply(
        self,
        *,
        pressure_constraint: FloatConstraint,
        inlet_stream: FluidStream,
        run_system: ConfigurationRunner,
    ) -> Solution[PressureControlConfiguration]:
        """
        Find a pressure-control configuration that meets the target.

        Args:
            pressure_constraint: Target outlet pressure.
            inlet_stream: The inlet fluid stream (read-only context).
            run_system: Callback that applies a PressureControlConfiguration
                        to the mutable process system and returns the
                        resulting outlet stream.

        Returns:
            Solution wrapping the configuration found.
            solution.success is False when the target cannot be met.
        """
        ...
