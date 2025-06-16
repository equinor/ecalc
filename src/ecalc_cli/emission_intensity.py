from libecalc.common.time_utils import Frequency
from libecalc.common.units import Unit
from libecalc.common.utils.rates import TimeSeriesRate, TimeSeriesVolumesCumulative
from libecalc.domain.emission.emission_intensity import EmissionIntensity, EmissionIntensityResults
from libecalc.presentation.json_result.result.emission import EmissionIntensityResult, EmissionResult


class EmissionIntensityCalculator:
    def __init__(
        self, hydrocarbon_export_rate: TimeSeriesRate, emissions: dict[str, EmissionResult], frequency: Frequency
    ):
        self.hydrocarbon_export_rate = hydrocarbon_export_rate
        self.emissions = emissions
        self.frequency = frequency

        self._hydrocarbon_export_cumulative = hydrocarbon_export_rate.to_volumes().cumulative()
        self._intensity_calculator_sm3 = EmissionIntensity(
            emission_cumulative=self._cumulative_rate_kg(),
            hydrocarbon_export_cumulative=self._hydrocarbon_export_cumulative.to_unit(Unit.STANDARD_CUBIC_METER),
        )
        self._intensity_calculator_boe = EmissionIntensity(
            emission_cumulative=self._cumulative_rate_kg(),
            hydrocarbon_export_cumulative=self._hydrocarbon_export_cumulative.to_unit(Unit.BOE),
        )

    def get_results(self) -> EmissionIntensityResults:
        """
        Calculate emission intensity results based on hydrocarbon export and emissions data.

        Returns:
            EmissionIntensityResults: The calculated emission intensity results.
        """
        emission_intensities = []

        if self.frequency == Frequency.YEAR:
            intensity_yearly_sm3 = self._intensity_calculator_sm3.calculate_for_periods()
            intensity_yearly_boe = self._intensity_calculator_boe.calculate_for_periods()
        else:
            intensity_yearly_sm3 = None
            intensity_yearly_boe = None

        emission_intensities.append(
            EmissionIntensityResult(
                name=self._co2_emission_result().name,
                periods=self._co2_emission_result().periods,
                intensity_sm3=self._intensity_calculator_sm3.calculate_cumulative(),
                intensity_boe=self._intensity_calculator_boe.calculate_cumulative(),
                intensity_yearly_sm3=intensity_yearly_sm3,
                intensity_yearly_boe=intensity_yearly_boe,
            )
        )
        return EmissionIntensityResults(results=emission_intensities)

    def _co2_emission_result(self) -> EmissionResult:
        return next((value for key, value in self.emissions.items() if key.lower() == "co2"))

    def _cumulative_rate_kg(self) -> TimeSeriesVolumesCumulative:
        return self._co2_emission_result().get_cumulative_kg()
