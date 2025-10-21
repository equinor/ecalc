from __future__ import annotations

from typing import Self

from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    TimeSeriesFloat,
    TimeSeriesRate,
    TimeSeriesStreamDayRate,
    TimeSeriesVolumesCumulative,
)
from libecalc.presentation.json_result.result.tabular_time_series import (
    TabularTimeSeries,
)


class EmissionResult(TabularTimeSeries):
    """The emissions for a result component."""

    name: str
    rate: TimeSeriesRate
    cumulative: TimeSeriesVolumesCumulative

    def get_cumulative_kg(self) -> TimeSeriesVolumesCumulative:
        """Returns cumulative CO2 emissions in kilograms."""
        return self.rate.to_volumes().to_unit(Unit.KILO).cumulative()


class PartialEmissionResult(TabularTimeSeries):
    """The partial emissions - a direct translation from the core emission results"""

    name: str
    rate: TimeSeriesRate

    @classmethod
    def from_emission_core_result(
        cls, emission_rate: TimeSeriesStreamDayRate, emission_name: str, regularity: TimeSeriesFloat
    ) -> Self:
        return PartialEmissionResult(
            name=emission_name,
            periods=emission_rate.periods,
            rate=TimeSeriesRate.from_timeseries_stream_day_rate(emission_rate, regularity),
        )
