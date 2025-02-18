from libecalc.common.errors.exceptions import ProgrammingError
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    TimeSeriesIntensity,
    TimeSeriesVolumesCumulative,
)


class EmissionIntensity:
    """
    A class to calculate emission intensity based on cumulative emission and hydrocarbon export data.

    This class provides methods to calculate both the cumulative emission intensity over the entire data range
    and the emission intensity for each individual period within the data range.

    Attributes:
        emission_cumulative (TimeSeriesVolumesCumulative): The cumulative emission data.
        hydrocarbon_export_cumulative (TimeSeriesVolumesCumulative): The cumulative hydrocarbon export data.
        unit (Unit): The unit of measurement for the intensity.
        periods (list): The periods over which the data is calculated. Used only when calculating intensity for each period within the data range.
    """

    def __init__(
        self,
        emission_cumulative: TimeSeriesVolumesCumulative,
        hydrocarbon_export_cumulative: TimeSeriesVolumesCumulative,
    ):
        if emission_cumulative.unit == Unit.KILO and hydrocarbon_export_cumulative.unit == Unit.STANDARD_CUBIC_METER:
            unit = Unit.KG_SM3
        else:
            raise ProgrammingError(
                f"Unable to divide unit '{emission_cumulative.unit}' by unit '{hydrocarbon_export_cumulative.unit}'. Please add unit conversion."
            )

        if len(emission_cumulative) != len(hydrocarbon_export_cumulative):
            raise ValueError(
                f"The lengths of the emission- and hydrocarbon export time vectors must be the same. "
                f"Got {len(emission_cumulative)} and {len(hydrocarbon_export_cumulative)}."
            )

        self.emission_cumulative = emission_cumulative
        self.hydrocarbon_export_cumulative = hydrocarbon_export_cumulative
        self.unit = unit
        self.periods = emission_cumulative.periods

    def calculate_for_periods(self) -> TimeSeriesIntensity:
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

    def calculate_cumulative(self) -> TimeSeriesIntensity:
        """
        Calculate the cumulative emission intensity over the entire data range.
        """
        intensity = self.emission_cumulative / self.hydrocarbon_export_cumulative

        return TimeSeriesIntensity(
            periods=self.periods,
            values=intensity.values,
            unit=self.unit,
            emissions=self.emission_cumulative,
            hc_export=self.hydrocarbon_export_cumulative,
        )
