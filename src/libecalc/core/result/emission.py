from __future__ import annotations

from datetime import datetime
from typing import List

from libecalc.common.units import Unit
from libecalc.common.utils.rates import TimeSeriesStreamDayRate
from libecalc.core.result.base import EcalcResultBaseModel


class EmissionResult(EcalcResultBaseModel):
    """The emissions for a result component."""

    name: str
    timesteps: List[datetime]
    rate: TimeSeriesStreamDayRate  # ton/day

    @classmethod
    def create_empty(cls, name: str, timesteps: List[datetime]):
        return cls(
            name=name,
            timesteps=timesteps,
            rate=TimeSeriesStreamDayRate(
                timesteps=timesteps,
                values=[0] * len(timesteps),
                unit=Unit.TONS_PER_DAY,
            ),
        )
