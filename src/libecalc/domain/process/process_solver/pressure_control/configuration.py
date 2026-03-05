from abc import ABC, abstractmethod
from dataclasses import dataclass

from libecalc.domain.process.value_objects.fluid_stream import FluidStream


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

    # Common ASV: single recirculation valve for the whole train
    recirculation_rate: float = 0.0  # Common ASV

    # Individual ASV pressure: per-stage recirculation rates
    recirculation_rates_per_stage: tuple[float, ...] | None = None

    # Individual ASV rate: fraction of available capacity recirculated per stage [0, 1]
    asv_rate_fraction: float | None = None  #

    # Choke
    upstream_delta_pressure: float = 0.0
    downstream_delta_pressure: float = 0.0


class ConfigurationRunner(ABC):
    """
    Applies a PressureControlConfiguration to the physical system and
    returns the resulting outlet stream.

    This is the single interface through which pressure control strategies interact
    with the physical system — they never touch the system directly.
    """

    @abstractmethod
    def run(self, configuration: PressureControlConfiguration) -> FluidStream: ...
