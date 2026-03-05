from abc import ABC, abstractmethod
from enum import StrEnum

from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.pressure_control.configuration import (
    ConfigurationRunner,
    PressureControlConfiguration,
)
from libecalc.domain.process.process_solver.solver import Solution


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
        target_pressure: FloatConstraint,
        input_cfg: PressureControlConfiguration,
        runner: ConfigurationRunner,
    ) -> Solution[PressureControlConfiguration]:
        """Find a configuration that meets the target pressure.

        Args:
            target_pressure: Target outlet pressure.
            input_cfg: Current configuration.
            runner: Applies a configuration to the physical system and
            propagates the stream through it.

        Returns:
            Solution wrapping the updated configuration.
        """
        ...
