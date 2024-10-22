from __future__ import annotations

from libecalc.common.time_utils import Periods
from libecalc.common.units import Unit
from libecalc.common.utils.rates import TimeSeriesStreamDayRate
from libecalc.core.result.base import EcalcResultBaseModel


class EmissionResult(EcalcResultBaseModel):
    """The emissions for a result component."""

    name: str
    periods: Periods
    rate: TimeSeriesStreamDayRate  # ton/day

    @classmethod
    def create_empty(cls, name: str, periods: Periods):
        return cls(
            name=name,
            periods=periods,
            rate=TimeSeriesStreamDayRate(
                periods=periods,
                values=[0] * len(periods),
                unit=Unit.TONS_PER_DAY,
            ),
        )
