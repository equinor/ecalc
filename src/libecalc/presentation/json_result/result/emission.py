from __future__ import annotations

from typing import Self

import pandas as pd

from libecalc.common.time_utils import Periods
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    TimeSeriesFloat,
    TimeSeriesRate,
    TimeSeriesVolumesCumulative,
)
from libecalc.core.result.emission import EmissionResult as EmissionCoreResult
from libecalc.domain.emission.time_series_intensity import TimeSeriesIntensity
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

    @classmethod
    def create_empty(cls, name: str, periods: Periods):
        """Empty placeholder for emissions, when needed

        Args:
            name:
            periods:

        Returns:

        """
        return cls(
            name=name,
            periods=periods,
            rate=TimeSeriesRate(
                periods=periods,
                values=[0] * len(periods),
                unit=Unit.TONS_PER_DAY,
            ),
            cumulative=TimeSeriesVolumesCumulative(
                periods=periods,
                values=[0] * len(periods),
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
            periods=emission_result.periods,
            rate=TimeSeriesRate.from_timeseries_stream_day_rate(emission_result.rate, regularity),
        )


class EmissionIntensityResult(TabularTimeSeries):
    name: str
    intensity_sm3: TimeSeriesIntensity
    intensity_boe: TimeSeriesIntensity
    intensity_yearly_sm3: TimeSeriesIntensity | None = None
    intensity_yearly_boe: TimeSeriesIntensity | None = None

    def to_dataframe(self, prefix: str | None = None) -> pd:
        dfs = []
        for attr, value in self.__dict__.items():
            if isinstance(value, TimeSeriesIntensity) and value is not None:
                unit_str = str(value.unit.value) if hasattr(value.unit, "value") else str(value.unit)
                col_name = f"{prefix}.{attr}[{unit_str}]" if prefix else f"{attr}[{unit_str}]"
                df = pd.DataFrame({col_name: value.values}, index=[p.start for p in value.periods])
                df.index.name = "period"
                dfs.append(df)
        if dfs:
            result_df = pd.concat(dfs, axis=1)
            result_df.index.name = "period"
            return result_df
        return pd.DataFrame()
