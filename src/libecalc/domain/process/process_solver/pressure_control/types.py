from dataclasses import dataclass
from typing import Literal

from libecalc.domain.process.value_objects.fluid_stream import FluidStream

PressureControlPolicyName = Literal[
    "COMMON_ASV",
    "DOWNSTREAM_CHOKE",
    "UPSTREAM_CHOKE",
]
CapacityPolicyName = Literal[
    "NONE",
    "COMMON_ASV_MIN_FLOW",
]


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
    recirculation_rate: float = 0.0
    upstream_delta_pressure: float = 0.0
    downstream_delta_pressure: float = 0.0


@dataclass(frozen=True)
class PressureControlResult:
    """
    Convenience wrapper used by the outer speed solver: configuration + corresponding outlet stream.
    """

    outlet_stream: FluidStream
    configuration: PressureControlConfiguration
