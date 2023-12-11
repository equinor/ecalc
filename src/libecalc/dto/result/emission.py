from __future__ import annotations

from datetime import datetime
from typing import List

from typing_extensions import Self

from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    TimeSeriesFloat,
    TimeSeriesIntensity,
    TimeSeriesRate,
    TimeSeriesVolumesCumulative,
)
from libecalc.core.result.emission import EmissionResult as EmissionCoreResult
from libecalc.dto.result.tabular_time_series import TabularTimeSeries


class EmissionResult(TabularTimeSeries):
    """The emissions for a result component."""

    name: str
    rate: TimeSeriesRate
    cumulative: TimeSeriesVolumesCumulative

    @classmethod
    def create_empty(cls, name: str, timesteps: List[datetime]):
        """Empty placeholder for emissions, when needed

        Args:
            name:
            timesteps:

        Returns:

        """
        return cls(
            name=name,
            timesteps=timesteps,
            rate=TimeSeriesRate(
                timesteps=timesteps,
                values=[0] * len(timesteps),
                unit=Unit.TONS_PER_DAY,
            ),
            cumulative=TimeSeriesVolumesCumulative(
                timesteps=timesteps,
                values=[0] * len(timesteps),
                unit=Unit.TONS,
            ),
        )


class PartialEmissionResult(TabularTimeSeries):
    """The partial emissions - a direct translation from the core emission results"""

    name: str
    rate: TimeSeriesRate

    @classmethod
    def from_emission_core_result(cls, emission_result: EmissionCoreResult, regularity: TimeSeriesFloat) -> Self:
        return PartialEmissionResult(
            name=emission_result.name,
            timesteps=emission_result.timesteps,
            rate=TimeSeriesRate.from_timeseries_stream_day_rate(emission_result.rate, regularity),
        )


class EmissionIntensityResult(TabularTimeSeries):
    name: str
    intensity_sm3: TimeSeriesIntensity
    intensity_boe: TimeSeriesIntensity
    intensity_yearly_sm3: TimeSeriesIntensity
    intensity_yearly_boe: TimeSeriesIntensity
