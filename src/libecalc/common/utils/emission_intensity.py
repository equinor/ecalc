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

    def calculate_intensity_periods(self):
        """
        Calculate the emission intensity for each period over the entire data range.
        """
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
        """
        Calculate the cumulative emission intensity over the entire data period.
        """
        intensity = self.emission_cumulative / self.hydrocarbon_export_cumulative

        return TimeSeriesIntensity(
            periods=self.periods,
            values=intensity.values,
            unit=self.unit,
            emissions=self.emission_cumulative,
            hc_export=self.hydrocarbon_export_cumulative,
        )
