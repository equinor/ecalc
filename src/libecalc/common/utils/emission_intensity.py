from datetime import datetime

from libecalc.common.time_utils import Period, Periods
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
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

    def calculate_intensity_periods(self):
        emission_volumes = self.emission_cumulative.to_volumes()
        hydrocarbon_export_volumes = self.hydrocarbon_export_cumulative.to_volumes()

        intensity = emission_volumes / hydrocarbon_export_volumes

        return TimeSeriesIntensity(
            periods=self.periods,
            values=intensity.values,
            unit=self.unit,
            emissions=emission_volumes,
            hc_export=hydrocarbon_export_volumes,
        )

    def calculate_intensity_cumulative(self) -> TimeSeriesIntensity:
        """Write description here"""
        intensity = self.emission_cumulative / self.hydrocarbon_export_cumulative

        return TimeSeriesIntensity(
            periods=self.periods,
            values=intensity.values,
            unit=self.unit,
            emissions=self.emission_cumulative,
            hc_export=self.hydrocarbon_export_cumulative,
        )
