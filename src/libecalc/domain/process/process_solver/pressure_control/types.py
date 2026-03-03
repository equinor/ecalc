from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

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
    recirculation_rates_per_stage: tuple[float, ...] | None = None  # Prepare for individual ASV
    upstream_delta_pressure: float = 0.0
    downstream_delta_pressure: float = 0.0


RunPressureControlCfg = Callable[[PressureControlConfiguration], FluidStream]
