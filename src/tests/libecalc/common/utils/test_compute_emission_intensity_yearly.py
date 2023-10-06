import math
from datetime import datetime
from typing import List, Tuple

import numpy as np
from libecalc.common.units import Unit
from libecalc.common.utils.calculate_emission_intensity import (
    compute_emission_intensity_by_yearly_buckets,
    compute_emission_intensity_yearly,
)
from libecalc.common.utils.rates import Rates, TimeSeriesRate, TimeSeriesVolumes
from libecalc.dto.types import RateType


def _setup_intensity_testcase(
    time_vector: List[datetime],
) -> Tuple[TimeSeriesRate, TimeSeriesVolumes, TimeSeriesRate, TimeSeriesVolumes]:
    number_of_timesteps = len(time_vector)
    emission_rate = np.full(shape=number_of_timesteps, fill_value=1.0)
    hcexport_rate = np.asarray(list(range(number_of_timesteps, 0, -1)))

    emission_cumulative = Rates.compute_cumulative_volumes_from_daily_rates(rates=emission_rate, time_steps=time_vector)
    hcexport_cumulative = Rates.compute_cumulative_volumes_from_daily_rates(rates=hcexport_rate, time_steps=time_vector)

    return (
        TimeSeriesRate(
            values=list(emission_rate),
            timesteps=time_vector,
            unit=Unit.KILO_PER_DAY,
            rate_type=RateType.STREAM_DAY,
            regularity=[1.0],
        ),
        TimeSeriesVolumes(values=list(emission_cumulative), timesteps=time_vector, unit=Unit.KILO),
        TimeSeriesRate(
            values=list(hcexport_rate),
            timesteps=time_vector,
            unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
            rate_type=RateType.STREAM_DAY,
            regularity=[1.0],
        ),
        TimeSeriesVolumes(values=list(hcexport_cumulative), timesteps=time_vector, unit=Unit.STANDARD_CUBIC_METER),
    )


class TestEmissionIntensityByYearlyBuckets:
    def test_emission_intensity_single_year(self):
        emission_intensity = compute_emission_intensity_by_yearly_buckets(
            emission_cumulative=TimeSeriesVolumes(values=[0.0], timesteps=[datetime(2000, 7, 1)], unit=Unit.KILO),
            hydrocarbon_export_cumulative=TimeSeriesVolumes(
                values=[0.0], timesteps=[datetime(2000, 7, 1)], unit=Unit.KILO
            ),
        )
        assert len(emission_intensity) == 1
        assert math.isnan(emission_intensity.values[0])

    def test_emission_intensity(self):
        # Test where time vector starts at 1.1 and all year starts are in time vector
        time_vector = [
            datetime(year=2000, month=1, day=1),
            datetime(year=2000, month=7, day=2),
            datetime(year=2001, month=1, day=1),
            datetime(year=2001, month=7, day=2),
            datetime(year=2002, month=1, day=1),
            datetime(year=2002, month=7, day=2),
        ]

        (
            emission_rate,
            emission_cumulative,
            hcexport_rate,
            hcexport_cumulative,
        ) = _setup_intensity_testcase(time_vector=time_vector)
        # Yearly emission intensities
        emission_2000 = emission_cumulative.values[2]
        emission_2001 = emission_cumulative.values[4] - emission_cumulative.values[2]
        emission_2002 = emission_cumulative.values[5] - emission_cumulative.values[4]
        hcexport_2000 = hcexport_cumulative.values[2]
        hcexport_2001 = hcexport_cumulative.values[4] - hcexport_cumulative.values[2]
        hcexport_2002 = hcexport_cumulative.values[5] - hcexport_cumulative.values[4]
        intensity_2000 = emission_2000 / hcexport_2000
        intensity_2001 = emission_2001 / hcexport_2001
        intensity_2002 = emission_2002 / hcexport_2002

        emission_intensity_yearly = compute_emission_intensity_by_yearly_buckets(
            emission_cumulative=emission_cumulative,
            hydrocarbon_export_cumulative=hcexport_cumulative,
        )

        assert np.all(emission_intensity_yearly.values[0:2] == intensity_2000)
        assert np.all(emission_intensity_yearly.values[2:4] == intensity_2001)
        assert np.all(emission_intensity_yearly.values[4:6] == intensity_2002)

    def test_emission_intensity_without_start_of_the_year_in_time_vector(self):
        # Test where the dates in time_vector are not at year start
        time_vector = [
            datetime(year=2000, month=7, day=2, hour=12),
            datetime(year=2001, month=7, day=2, hour=12),
            datetime(year=2002, month=7, day=2, hour=12),
        ]

        (
            emission_rate,
            emission_cumulative,
            hcexport_rate,
            hcexport_cumulative,
        ) = _setup_intensity_testcase(time_vector=time_vector)
        emission_2000 = 365 / 2 * emission_rate.values[0]
        emission_2001 = 365 / 2 * (emission_rate.values[0] + emission_rate.values[1])
        emission_2002 = 365 / 2 * emission_rate.values[1]
        hcexport_2000 = 365 / 2 * hcexport_rate.values[0]
        hcexport_2001 = 365 / 2 * (hcexport_rate.values[0] + hcexport_rate.values[1])
        hcexport_2002 = 365 / 2 * hcexport_rate.values[1]
        intensity_2000 = emission_2000 / hcexport_2000
        intensity_2001 = emission_2001 / hcexport_2001
        intensity_2002 = emission_2002 / hcexport_2002
        emission_intensity_yearly = compute_emission_intensity_by_yearly_buckets(
            emission_cumulative=emission_cumulative,
            hydrocarbon_export_cumulative=hcexport_cumulative,
        )

        assert emission_intensity_yearly.values[0] == intensity_2000
        assert emission_intensity_yearly.values[1] == intensity_2001
        assert emission_intensity_yearly.values[2] == intensity_2002

    def test_emission_intensity_year_not_present_in_time_vector(self):
        # Test where some years are not present in time_vector
        time_vector = [
            datetime(year=2000, month=7, day=2, hour=12),
            datetime(year=2002, month=7, day=2, hour=12),
            datetime(year=2003, month=7, day=2, hour=12),
        ]

        (
            emission_rate,
            emission_cumulative,
            hcexport_rate,
            hcexport_cumulative,
        ) = _setup_intensity_testcase(time_vector=time_vector)
        emission_2000 = 365 / 2 * emission_rate.values[0]
        emission_2002 = 365 / 2 * (emission_rate.values[0] + emission_rate.values[1])
        emission_2003 = 365 / 2 * emission_rate.values[1]
        hcexport_2000 = 365 / 2 * hcexport_rate.values[0]
        hcexport_2002 = 365 / 2 * (hcexport_rate.values[0] + hcexport_rate.values[1])
        hcexport_2003 = 365 / 2 * hcexport_rate.values[1]
        intensity_2000 = emission_2000 / hcexport_2000
        intensity_2002 = emission_2002 / hcexport_2002
        intensity_2003 = emission_2003 / hcexport_2003
        emission_intensity_yearly = compute_emission_intensity_by_yearly_buckets(
            emission_cumulative=emission_cumulative,
            hydrocarbon_export_cumulative=hcexport_cumulative,
        )

        assert emission_intensity_yearly.values[0] == intensity_2000
        assert emission_intensity_yearly.values[1] == intensity_2002
        assert emission_intensity_yearly.values[2] == intensity_2003


class TestEmissionIntensityYearly:
    def test_emission_intensity_single_year(self):
        emission_intensity = compute_emission_intensity_yearly(
            time_vector=[datetime(2000, 7, 1)],
            emission_cumulative=[0.0],
            hydrocarbon_export_cumulative=[0.0],
        )
        assert len(emission_intensity) == 1
        assert math.isnan(emission_intensity[0])

    def test_emission_intensity(self):
        # Test where time vector starts at 1.1 and all year starts are in time vector
        time_vector = [
            datetime(year=2000, month=1, day=1),
            datetime(year=2000, month=7, day=2),
            datetime(year=2001, month=1, day=1),
            datetime(year=2001, month=7, day=2),
            datetime(year=2002, month=1, day=1),
            datetime(year=2002, month=7, day=2),
        ]

        (
            emission_rate,
            emission_cumulative,
            hcexport_rate,
            hcexport_cumulative,
        ) = _setup_intensity_testcase(time_vector=time_vector)
        # Yearly emission intensities
        emission_2000 = emission_cumulative.values[2]
        emission_2001 = emission_cumulative.values[4] - emission_cumulative.values[2]
        emission_2002 = emission_cumulative.values[5] - emission_cumulative.values[4]
        hcexport_2000 = hcexport_cumulative.values[2]
        hcexport_2001 = hcexport_cumulative.values[4] - hcexport_cumulative.values[2]
        hcexport_2002 = hcexport_cumulative.values[5] - hcexport_cumulative.values[4]
        intensity_2000 = emission_2000 / hcexport_2000
        intensity_2001 = emission_2001 / hcexport_2001
        intensity_2002 = emission_2002 / hcexport_2002

        emission_intensity_yearly = compute_emission_intensity_yearly(
            emission_cumulative=emission_cumulative.values,
            hydrocarbon_export_cumulative=hcexport_cumulative.values,
            time_vector=emission_cumulative.timesteps,
        )

        assert np.all(emission_intensity_yearly[0] == intensity_2000)
        assert np.all(emission_intensity_yearly[1] == intensity_2001)
        assert np.all(emission_intensity_yearly[2] == intensity_2002)

    def test_emission_intensity_without_start_of_the_year_in_time_vector(self):
        # Test where the dates in time_vector are not at year start
        time_vector = [
            datetime(year=2000, month=7, day=2, hour=12),
            datetime(year=2001, month=7, day=2, hour=12),
            datetime(year=2002, month=7, day=2, hour=12),
        ]

        (
            emission_rate,
            emission_cumulative,
            hcexport_rate,
            hcexport_cumulative,
        ) = _setup_intensity_testcase(time_vector=time_vector)
        emission_2000 = 365 / 2 * emission_rate.values[0]
        emission_2001 = 365 / 2 * (emission_rate.values[0] + emission_rate.values[1])
        emission_2002 = 365 / 2 * emission_rate.values[1]
        hcexport_2000 = 365 / 2 * hcexport_rate.values[0]
        hcexport_2001 = 365 / 2 * (hcexport_rate.values[0] + hcexport_rate.values[1])
        hcexport_2002 = 365 / 2 * hcexport_rate.values[1]
        intensity_2000 = emission_2000 / hcexport_2000
        intensity_2001 = emission_2001 / hcexport_2001
        intensity_2002 = emission_2002 / hcexport_2002
        emission_intensity_yearly = compute_emission_intensity_yearly(
            emission_cumulative=emission_cumulative.values,
            hydrocarbon_export_cumulative=hcexport_cumulative.values,
            time_vector=emission_cumulative.timesteps,
        )

        assert emission_intensity_yearly[0] == intensity_2000
        assert emission_intensity_yearly[1] == intensity_2001
        assert emission_intensity_yearly[2] == intensity_2002

    def test_emission_intensity_year_not_present_in_time_vector(self):
        # Test where some years are not present in time_vector
        time_vector = [
            datetime(year=2000, month=7, day=2, hour=12),
            datetime(year=2002, month=7, day=2, hour=12),
            datetime(year=2003, month=7, day=2, hour=12),
        ]

        (
            emission_rate,
            emission_cumulative,
            hcexport_rate,
            hcexport_cumulative,
        ) = _setup_intensity_testcase(time_vector=time_vector)
        emission_2000 = 365 / 2 * emission_rate.values[0]
        emission_2001 = 365 / 2 * emission_rate.values[0]
        emission_2002 = 365 / 2 * (emission_rate.values[0] + emission_rate.values[1])
        emission_2003 = 365 / 2 * emission_rate.values[1]
        hcexport_2000 = 365 / 2 * hcexport_rate.values[0]
        hcexport_2001 = 365 / 2 * hcexport_rate.values[0]
        hcexport_2002 = 365 / 2 * (hcexport_rate.values[0] + hcexport_rate.values[1])
        hcexport_2003 = 365 / 2 * hcexport_rate.values[1]
        intensity_2000 = emission_2000 / hcexport_2000
        intensity_2001 = emission_2001 / hcexport_2001
        intensity_2002 = emission_2002 / hcexport_2002
        intensity_2003 = emission_2003 / hcexport_2003
        emission_intensity_yearly = compute_emission_intensity_yearly(
            emission_cumulative=emission_cumulative.values,
            hydrocarbon_export_cumulative=hcexport_cumulative.values,
            time_vector=emission_cumulative.timesteps,
        )

        assert emission_intensity_yearly[0] == intensity_2000
        assert emission_intensity_yearly[1] == intensity_2001
        assert emission_intensity_yearly[2] == intensity_2002
        assert emission_intensity_yearly[3] == intensity_2003
