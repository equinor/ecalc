from __future__ import annotations

from datetime import datetime
from typing import List

from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    TimeSeriesFloat,
    TimeSeriesIntensity,
    TimeSeriesRate,
    TimeSeriesVolumesCumulative,
)
from libecalc.core.result.emission import EmissionResult as EmissionCoreResult
from libecalc.dto.result.simple import SimpleEmissionResult
from libecalc.dto.result.tabular_time_series import TabularTimeSeries
from typing_extensions import Self


class EmissionResult(TabularTimeSeries):
    """The emissions for a result component."""

    name: str
    rate: TimeSeriesRate
    cumulative: TimeSeriesVolumesCumulative
    tax: TimeSeriesRate
    tax_cumulative: TimeSeriesVolumesCumulative
    quota: TimeSeriesRate
    quota_cumulative: TimeSeriesVolumesCumulative

    def simple_result(self):
        return SimpleEmissionResult(**self.dict())

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
            tax=TimeSeriesRate(
                timesteps=timesteps,
                values=[0] * len(timesteps),
                unit=Unit.NORWEGIAN_KRONER_PER_DAY,
            ),
            tax_cumulative=TimeSeriesVolumesCumulative(
                timesteps=timesteps,
                values=[0] * len(timesteps),
                unit=Unit.NORWEGIAN_KRONER,
            ),
            quota=TimeSeriesRate(
                timesteps=timesteps,
                values=[0] * len(timesteps),
                unit=Unit.NORWEGIAN_KRONER_PER_DAY,
            ),
            quota_cumulative=TimeSeriesVolumesCumulative(
                timesteps=timesteps,
                values=[0] * len(timesteps),
                unit=Unit.NORWEGIAN_KRONER,
            ),
        )


class PartialEmissionResult(TabularTimeSeries):
    """The partial emissions - a direct translation from the core emission results"""

    name: str
    rate: TimeSeriesRate
    tax: TimeSeriesRate
    quota: TimeSeriesRate

    @classmethod
    def from_emission_core_result(cls, emission_result: EmissionCoreResult, regularity: TimeSeriesFloat) -> Self:
        return PartialEmissionResult(
            name=emission_result.name,
            timesteps=emission_result.timesteps,
            rate=TimeSeriesRate.from_timeseries_stream_day_rate(emission_result.rate, regularity),
            tax=TimeSeriesRate.from_timeseries_stream_day_rate(emission_result.tax, regularity),
            quota=TimeSeriesRate.from_timeseries_stream_day_rate(emission_result.quota, regularity),
        )


class EmissionIntensityResult(TabularTimeSeries):
    name: str
    intensity_sm3: TimeSeriesIntensity
    intensity_boe: TimeSeriesIntensity
    intensity_yearly_sm3: TimeSeriesIntensity
    intensity_yearly_boe: TimeSeriesIntensity
