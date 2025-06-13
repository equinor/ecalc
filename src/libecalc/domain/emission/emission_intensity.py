from typing import Self

import pandas as pd

from libecalc.common.errors.exceptions import ProgrammingError
from libecalc.common.time_utils import Frequency
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    TimeSeriesIntensity,
    TimeSeriesRate,
    TimeSeriesVolumesCumulative,
)
from libecalc.presentation.json_result.result.base import EcalcResultBaseModel
from libecalc.presentation.json_result.result.emission import EmissionIntensityResult, EmissionResult


class EmissionIntensityResults(EcalcResultBaseModel):
    results: list[EmissionIntensityResult]

    def resample(self, freq: Frequency) -> Self:
        return EmissionIntensityResults(results=[r.resample(freq) for r in self.results])


def emission_intensity_to_csv(emission_intensity_results, date_format) -> str:
    # emission_intensity_results.results is a list of EmissionIntensityResult
    dfs = []
    for result in emission_intensity_results.results:
        df = result.to_dataframe(prefix=result.name)
        # Drop yearly columns if all values are None
        for col in ["intensity_yearly_sm3", "intensity_yearly_boe"]:
            if col in df.columns and df[col].isnull().all():
                df = df.drop(columns=[col])

        dfs.append(df)
    if not dfs:
        combined_df = pd.DataFrame()
    else:
        combined_df = pd.concat(dfs, axis=1)
        combined_df.index = combined_df.index.strftime(date_format)
    csv_data = combined_df.to_csv(index_label="timesteps")
    return csv_data


def calculate_emission_intensity(
    hydrocarbon_export_rate: TimeSeriesRate,
    emissions: dict[str, EmissionResult],
    frequency: Frequency,
) -> EmissionIntensityResults:
    hydrocarbon_export_cumulative = hydrocarbon_export_rate.to_volumes().cumulative()
    emission_intensities = []

    co2_emission_result = next((value for key, value in emissions.items() if key.lower() == "co2"), None)
    if co2_emission_result is None:
        return EmissionIntensityResults(results=[])

    cumulative_rate_kg = co2_emission_result.rate.to_volumes().to_unit(Unit.KILO).cumulative()
    intensity = EmissionIntensity(
        emission_cumulative=cumulative_rate_kg,
        hydrocarbon_export_cumulative=hydrocarbon_export_cumulative,
    )
    intensity_sm3 = intensity.calculate_cumulative()

    if frequency == Frequency.YEAR:
        intensity_yearly_sm3 = intensity.calculate_for_periods()
        intensity_yearly_boe = intensity_yearly_sm3.to_unit(Unit.BOE)
    else:
        intensity_yearly_sm3 = None
        intensity_yearly_boe = None

    emission_intensities.append(
        EmissionIntensityResult(
            name=co2_emission_result.name,
            periods=co2_emission_result.periods,
            intensity_sm3=intensity_sm3,
            intensity_boe=intensity_sm3.to_unit(Unit.BOE),
            intensity_yearly_sm3=intensity_yearly_sm3,
            intensity_yearly_boe=intensity_yearly_boe,
        )
    )
    return EmissionIntensityResults(results=emission_intensities)


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
