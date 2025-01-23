from datetime import datetime
from typing import Optional

import numpy as np
import pandas as pd

from libecalc.common.time_utils import Period, Periods
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    TimeSeriesCalendarDayRate,
    TimeSeriesIntensity,
    TimeSeriesVolumesCumulative,
)


class EmissionIntensity:
    def __init__(
        self,
        emission_cumulative: TimeSeriesVolumesCumulative,
        hydrocarbon_export_cumulative: TimeSeriesVolumesCumulative,
        unit: Unit = Unit.KG_SM3,
    ):
        self.emission_cumulative = emission_cumulative
        self.hydrocarbon_export_cumulative = hydrocarbon_export_cumulative
        self.unit = unit
        self.periods = emission_cumulative.periods
        self.yearly_periods = self._create_yearly_periods()
        self.time_vector = self.periods.all_dates
        self.start_years = [period.start.year for period in self.periods]

    def _create_yearly_periods(self) -> Periods:
        yearly_periods = []
        added_periods = set()

        for period in self.periods:
            for year in range(period.start.year, period.end.year + 1):
                start_date = datetime(year, 1, 1)
                end_date = datetime(year + 1, 1, 1)
                period_tuple = (start_date, end_date)

                if period_tuple not in added_periods:
                    yearly_periods.append(Period(start=start_date, end=end_date))
                    added_periods.add(period_tuple)

        return Periods(yearly_periods)

    def _calculate_yearly_old(self) -> list[float]:
        """Standard emission intensity at time k, is the sum of emissions from startup until time k
        divided by the sum of export from startup until time k.
        Thus, intensity_k = ( sum_t=1:k emission(t) ) / ( sum_t=1:k export(t) ).
        The yearly emission intensity for year k is the sum of emissions in year k divided by
        the sum of export in year k (and thus independent of the years before year k)
        I.e. intensity_yearly_k = emission_year_k / export_year_k
        emission_year_k may be computed as emission_cumulative(1. january year=k+1) - emission_cumulative(1. january year=k)
        hcexport_year_k may be computed as hcexport_cumulative(1. january year=k+1) - hcexport_cumulative(1. january year=k)
        To be able to evaluate cumulative emission and hydrocarbon_export at 1. january each year, a linear interpolation function
        is created between the time vector and the cumulative function. To be able to treat time as the x-variable, this is
        first converted to number of seconds from the beginning of the time vector
        """

        df = pd.DataFrame(
            data={
                "emission_cumulative": self.emission_cumulative.values,
                "hydrocarbon_cumulative": self.hydrocarbon_export_cumulative.values,
            },
            index=self.emission_cumulative.end_dates,  # Assuming dates are aligned with cumulative values
        )

        # Reindex the DataFrame to match the time_vector and fill missing values
        df = df.reindex(self.time_vector).ffill().fillna(0)

        # df = pd.DataFrame(
        #     index=self.time_vector,
        #     data=list(zip(self.emission_cumulative.values, self.hydrocarbon_export_cumulative.values)),
        #     columns=["emission_cumulative", "hydrocarbon_cumulative"],
        # )

        # Extending the time vector back and forth 1 year used as padding when calculating yearly buckets.
        time_vector_interpolated = pd.date_range(
            start=datetime(self.time_vector[0].year - 1, 1, 1),
            end=datetime(self.time_vector[-1].year + 1, 1, 1),
            freq="YS",
        )

        # Linearly interpolating by time using the built-in functionality in Pandas.
        cumulative_interpolated: Optional[pd.DataFrame] = df.reindex(
            sorted(set(self.periods.all_dates).union(time_vector_interpolated))
        ).interpolate("time")

        if cumulative_interpolated is None:
            raise ValueError("Time interpolation of cumulative yearly emission intensity failed")

        cumulative_yearly = cumulative_interpolated.bfill().loc[time_vector_interpolated]

        # Remove the extrapolated timesteps
        emissions_per_year = np.diff(cumulative_yearly.emission_cumulative[1:])
        hcexport_per_year = np.diff(cumulative_yearly.hydrocarbon_cumulative[1:])

        yearly_emission_intensity = np.divide(
            emissions_per_year,
            hcexport_per_year,
            out=np.full_like(emissions_per_year, fill_value=np.nan),
            where=hcexport_per_year != 0,
        )

        return yearly_emission_intensity.tolist()

    def calculate_old(self) -> TimeSeriesCalendarDayRate:
        """Legacy code that computes yearly intensity and casts the results back to the original time-vector."""
        yearly_buckets = range(self.time_vector[0].year, self.time_vector[-1].year + 1)
        yearly_intensity = self._calculate_yearly()
        return TimeSeriesCalendarDayRate(
            periods=self.periods,
            values=[yearly_intensity[yearly_buckets.index(period.start.year)] for period in self.periods],
            unit=Unit.KG_SM3,
        )

    def calculate_periods(self):
        emission_volumes = self.emission_cumulative.to_volumes()
        hydrocarbon_export_volumes = self.hydrocarbon_export_cumulative.to_volumes()

        intensity = emission_volumes / hydrocarbon_export_volumes

        return TimeSeriesIntensity(
            periods=self.periods,
            values=intensity.values,
            unit=self.unit,
        )

    def calculate(self) -> TimeSeriesIntensity:
        """Write description here"""
        intensity = self.emission_cumulative / self.hydrocarbon_export_cumulative

        return TimeSeriesIntensity(
            periods=self.periods,
            values=intensity.values,
            unit=self.unit,
        )
