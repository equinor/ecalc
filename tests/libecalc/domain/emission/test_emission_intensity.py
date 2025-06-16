from datetime import datetime

import numpy as np

from libecalc.common import math
from libecalc.common.time_utils import Frequency, Periods, Period
from libecalc.common.units import Unit
from libecalc.common.utils.rates import TimeSeriesVolumesCumulative, TimeSeriesRate, RateType, TimeSeriesVolumes, Rates
from libecalc.domain.emission.emission_intensity import EmissionIntensity

boe_factor = 6.29


def _setup_intensity_testcase(
    periods: Periods,
) -> tuple[TimeSeriesRate, TimeSeriesVolumesCumulative, TimeSeriesRate, TimeSeriesVolumesCumulative]:
    number_of_periods = len(periods)
    emission_rate = np.full(shape=number_of_periods, fill_value=1.0)
    hcexport_rate = np.asarray(list(range(number_of_periods, 0, -1)))

    emission_cumulative = Rates.compute_cumulative_volumes_from_daily_rates(rates=emission_rate, periods=periods)
    hcexport_cumulative = Rates.compute_cumulative_volumes_from_daily_rates(rates=hcexport_rate, periods=periods)

    return (
        TimeSeriesRate(
            values=list(emission_rate),
            periods=periods,
            unit=Unit.KILO_PER_DAY,
            rate_type=RateType.STREAM_DAY,
            regularity=[1.0] * number_of_periods,
        ),
        TimeSeriesVolumesCumulative(values=list(emission_cumulative), periods=periods, unit=Unit.KILO),
        TimeSeriesRate(
            values=list(hcexport_rate),
            periods=periods,
            unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
            rate_type=RateType.STREAM_DAY,
            regularity=[1.0] * number_of_periods,
        ),
        TimeSeriesVolumesCumulative(values=list(hcexport_cumulative), periods=periods, unit=Unit.STANDARD_CUBIC_METER),
    )


class TestEmissionIntensityByPeriods:
    def test_emission_intensity_single_year(self):
        periods = Periods.create_periods(
            [datetime(2000, 7, 1), datetime(2001, 7, 1)],
            include_before=False,
            include_after=False,
        )
        emission_intensity = EmissionIntensity(
            emission_cumulative=TimeSeriesVolumes(values=[0.0], periods=periods, unit=Unit.KILO).cumulative(),
            hydrocarbon_export_cumulative=TimeSeriesVolumes(
                values=[0.0], periods=periods, unit=Unit.STANDARD_CUBIC_METER
            ).cumulative(),
        ).calculate_cumulative()
        assert len(emission_intensity.values) == 1
        assert math.isnan(emission_intensity.values[0])

    def test_emission_intensity(self):
        # Test where time vector starts at 1.1 and all year starts are in time vector
        periods = Periods(
            [
                Period(start=datetime(year=2000, month=1, day=1), end=datetime(2000, 7, 2)),
                Period(start=datetime(year=2000, month=7, day=2), end=datetime(2001, 1, 1)),
                Period(start=datetime(year=2001, month=1, day=1), end=datetime(2001, 7, 2)),
            ]
        )

        (
            emission_rate,
            emission_cumulative,
            hcexport_rate,
            hcexport_cumulative,
        ) = _setup_intensity_testcase(periods=periods)

        # Yearly emission intensities
        emission_period_1 = emission_cumulative.values[0]
        emission_period_2 = emission_cumulative.values[1] - emission_cumulative.values[0]
        emission_period_3 = emission_cumulative.values[2] - emission_cumulative.values[1]
        hcexport_period_1 = hcexport_cumulative.values[0]
        hcexport_period_2 = hcexport_cumulative.values[1] - hcexport_cumulative.values[0]
        hcexport_period_3 = hcexport_cumulative.values[2] - hcexport_cumulative.values[1]
        intensity_period_1 = emission_period_1 / hcexport_period_1
        intensity_period_2 = emission_period_2 / hcexport_period_2
        intensity_period_3 = emission_period_3 / hcexport_period_3

        emission_intensity_yearly = EmissionIntensity(
            emission_cumulative=emission_cumulative,
            hydrocarbon_export_cumulative=hcexport_cumulative,
        ).calculate_for_periods()
        # TODO: why did this fail?
        assert np.all(emission_intensity_yearly.values[0] == intensity_period_1)
        assert np.all(emission_intensity_yearly.values[1] == intensity_period_2)
        assert np.all(emission_intensity_yearly.values[2] == intensity_period_3)

    def test_emission_intensity_without_start_of_the_year_in_time_vector(self):
        # Test where the dates in time_vector are not at year start
        periods = Periods(
            [
                Period(
                    start=datetime(year=2000, month=7, day=2, hour=12), end=datetime(year=2001, month=7, day=2, hour=12)
                ),
                Period(
                    start=datetime(year=2001, month=7, day=2, hour=12), end=datetime(year=2002, month=7, day=2, hour=12)
                ),
            ]
        )
        (
            emission_rate,
            emission_cumulative,
            hcexport_rate,
            hcexport_cumulative,
        ) = _setup_intensity_testcase(periods=periods)

        emission_period_1 = 365 * emission_rate.values[0]
        emission_period_2 = 365 * emission_rate.values[1]
        hcexport_period_1 = 365 * hcexport_rate.values[0]
        hcexport_period_2 = 365 * hcexport_rate.values[1]
        intensity_period_1 = emission_period_1 / hcexport_period_1
        intensity_period_2 = emission_period_2 / hcexport_period_2

        emission_intensity_yearly = EmissionIntensity(
            emission_cumulative=emission_cumulative,
            hydrocarbon_export_cumulative=hcexport_cumulative,
        ).calculate_for_periods()

        assert emission_intensity_yearly.values[0] == intensity_period_1
        assert emission_intensity_yearly.values[1] == intensity_period_2

    def test_emission_intensity_year_not_present_in_time_vector(self):
        # Test where some years are not present in time_vector
        periods = Periods(
            [
                Period(
                    start=datetime(year=2000, month=7, day=2, hour=12), end=datetime(year=2002, month=7, day=2, hour=12)
                ),
                Period(
                    start=datetime(year=2002, month=7, day=2, hour=12), end=datetime(year=2003, month=7, day=2, hour=12)
                ),
            ]
        )
        (
            emission_rate,
            emission_cumulative,
            hcexport_rate,
            hcexport_cumulative,
        ) = _setup_intensity_testcase(periods=periods)
        emission_period_1 = 365 * 2 * emission_rate.values[0]
        emission_period_2 = 365 * emission_rate.values[1]
        hcexport_period_1 = 365 * 2 * hcexport_rate.values[0]
        hcexport_period_2 = 365 * hcexport_rate.values[1]
        intensity_period_1 = emission_period_1 / hcexport_period_1
        intensity_period_2 = emission_period_2 / hcexport_period_2
        emission_intensity_yearly = EmissionIntensity(
            emission_cumulative=emission_cumulative,
            hydrocarbon_export_cumulative=hcexport_cumulative,
        ).calculate_for_periods()

        assert emission_intensity_yearly.values[0] == intensity_period_1
        assert emission_intensity_yearly.values[1] == intensity_period_2

    def test_emission_resample_by_year(self):
        periods = Periods(
            [
                Period(start=datetime(year=2000, month=7, day=1), end=datetime(2001, 7, 1)),
                Period(start=datetime(year=2001, month=7, day=1), end=datetime(2002, 7, 1)),
            ]
        )

        (
            emission_rate,
            emission_cumulative,
            hcexport_rate,
            hcexport_cumulative,
        ) = _setup_intensity_testcase(periods=periods)

        resampled_hcexport = hcexport_cumulative.resample(Frequency.YEAR)
        resampled_emission = emission_cumulative.resample(Frequency.YEAR)

        resampled_intensity = EmissionIntensity(
            emission_cumulative=resampled_emission, hydrocarbon_export_cumulative=resampled_hcexport
        ).calculate_for_periods()

        # Calculate expected intensities
        expected_emission_2000 = emission_rate.values[0] * 365 / 2
        expected_emission_2001 = emission_rate.values[0] * 365 / 2 + emission_rate.values[1] * 365 / 2
        expected_hcexport_2000 = hcexport_rate.values[0] * 365 / 2
        expected_hcexport_2001 = hcexport_rate.values[0] * 365 / 2 + hcexport_rate.values[1] * 365 / 2

        expected_intensity_2000 = expected_emission_2000 / expected_hcexport_2000
        expected_intensity_2001 = expected_emission_2001 / expected_hcexport_2001

        assert resampled_intensity.values[0] == expected_intensity_2000
        assert math.isclose(resampled_intensity.values[1], expected_intensity_2001, rel_tol=1e-2)


class TestEmissionIntensityCumulative:
    def test_emission_intensity_single_year(self):
        periods = Periods.create_periods(
            [datetime(2000, 7, 1), datetime(2000, 12, 31, 23, 59, 59)],
            include_before=False,
            include_after=False,
        )

        emission_cumulative_single_year = TimeSeriesVolumesCumulative(
            periods=periods,
            values=[0.0],
            unit=Unit.KILO,
        )
        hydrocarbon_export_cumulative_single_year = TimeSeriesVolumesCumulative(
            periods=periods,
            values=[0.0],
            unit=Unit.STANDARD_CUBIC_METER,
        )

        emission_intensity = EmissionIntensity(
            emission_cumulative=emission_cumulative_single_year,
            hydrocarbon_export_cumulative=hydrocarbon_export_cumulative_single_year,
        ).calculate_cumulative()

        assert len(emission_intensity.values) == 1
        assert math.isnan(emission_intensity.values[0])

    def test_emission_intensity(self):
        periods = Periods(
            [
                Period(start=datetime(year=2000, month=1, day=1), end=datetime(year=2000, month=7, day=2)),
                Period(start=datetime(year=2000, month=7, day=2), end=datetime(year=2001, month=1, day=1)),
                Period(start=datetime(year=2001, month=1, day=1), end=datetime(year=2001, month=7, day=2)),
            ]
        )

        (
            emission_rate,
            emission_cumulative,
            hcexport_rate,
            hcexport_cumulative,
        ) = _setup_intensity_testcase(periods=periods)

        # Yearly emission intensities
        emission = emission_cumulative.values[-1]
        hcexport = hcexport_cumulative.values[-1]
        intensity = emission / hcexport

        emission_intensity = EmissionIntensity(
            emission_cumulative=emission_cumulative, hydrocarbon_export_cumulative=hcexport_cumulative
        ).calculate_cumulative()

        assert emission_intensity.values[-1] == intensity
