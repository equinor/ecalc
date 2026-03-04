from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class PressureControlPolicyName(StrEnum):
    NONE = "NONE"
    COMMON_ASV = "COMMON_ASV"
    INDIVIDUAL_ASV_RATE = "INDIVIDUAL_ASV_RATE"
    INDIVIDUAL_ASV_PRESSURE = "INDIVIDUAL_ASV_PRESSURE"
    DOWNSTREAM_CHOKE = "DOWNSTREAM_CHOKE"
    UPSTREAM_CHOKE = "UPSTREAM_CHOKE"


class CapacityPolicyName(StrEnum):
    NONE = "NONE"
    COMMON_ASV_MIN_FLOW = "COMMON_ASV_MIN_FLOW"
    INDIVIDUAL_ASV_MIN_FLOW = "INDIVIDUAL_ASV_MIN_FLOW"


@dataclass(frozen=True)
class PressureControlConfiguration:
    """
    Full configuration needed to evaluate a pressure-controlled compressor train.

    Notes:
      - `speed` is the outer degree of freedom for variable speed trains.
      - `recirculation_rate` is used both for capacity handling (min flow) and for ASV pressure control.
      - `upstream_delta_pressure` / `downstream_delta_pressure` represent choking to reduce outlet pressure.
    """

    speed: float
    recirculation_rate: float = 0.0  # Common ASV
    recirculation_rates_per_stage: tuple[float, ...] | None = None  # Individual ASV
    asv_rate_fraction: float | None = None
    upstream_delta_pressure: float = 0.0
    downstream_delta_pressure: float = 0.0


# Evaluates the full compressor train for a given configuration and returns the outlet stream.
# Closes over shaft, recirculation loops, inlet stream, and fluid service.
RunPressureControlCfg = Callable[[PressureControlConfiguration], FluidStream]


# Evaluates a single compressor stage for a given recirculation rate and returns the outlet stream.
class StageRunner(ABC):
    @abstractmethod
    def run(self, recirculation_rate: float) -> FluidStream: ...

    @abstractmethod
    def get_recirculation_boundary(self) -> Boundary: ...

    @abstractmethod
    def get_minimum_recirculation_rate(self) -> float: ...
