from datetime import datetime

import numpy as np
import pytest
from pydantic import ValidationError

from libecalc.common.time_utils import Frequency, Period, Periods
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    Rates,
    RateType,
    TimeSeriesBoolean,
    TimeSeriesFloat,
    TimeSeriesRate,
    TimeSeriesVolumes,
    TimeSeriesVolumesCumulative,
)


def test_compute_stream_day_rate():
    calendar_day_rate = np.asarray([1.0, 2.0, 3.0])
    regularity = [0.9, 0.8, 0.99]
    np.testing.assert_allclose(
        Rates.to_stream_day(calendar_day_rates=calendar_day_rate, regularity=regularity),
        np.divide(calendar_day_rate, regularity, out=np.zeros_like(calendar_day_rate), where=regularity != 0),
    )


class TestComputeCumulative:
    def test_compute_cumulative_from_daily_rate(self):
        """Be aware. The rates are assumed to be daily."""
        cumulative = Rates.compute_cumulative_volumes_from_daily_rates(
            rates=np.array([1, 1, 1, 1]),
            periods=Periods.create_periods(
                times=[datetime(2000, 1, n) for n in range(1, 6)],
                include_before=False,
                include_after=False,
            ),
        )
        assert cumulative.tolist() == [1, 2, 3, 4]

    def test_compute_cumulative_from_rates_and_delta_time(self):
        # Test for correct cumulative calculation
        time_steps = [
            datetime(2023, 1, 1),
            datetime(2023, 1, 2),
            datetime(2023, 1, 4),
            datetime(2023, 1, 5),
            datetime(2023, 1, 8),
            datetime(2023, 1, 13),
            datetime(2023, 1, 14),
        ]
        rates = np.array([1, 1.5, 1.5, 2, 1, 1.3])
        output = Rates.compute_cumulative_volumes_from_daily_rates(
            rates=rates,
            periods=Periods.create_periods(
                times=time_steps,
                include_before=False,
                include_after=False,
            ),
        )
        assert output.tolist() == [1.0, 4.0, 5.5, 11.5, 16.5, 17.8]

    def test_compute_cumulative_from_rates_and_delta_time_simple_data(self):
        # 3 consecutive days [2022.01.01, 2022.01.03];
        datetimes = [
            datetime(year=2022, month=1, day=1),
            datetime(year=2022, month=1, day=2),
            datetime(year=2022, month=1, day=3),
        ]

        # 1 per day
        rate_vector = [1, 1]

        cumulative = Rates.compute_cumulative_volumes_from_daily_rates(
            rates=rate_vector,
            periods=Periods.create_periods(
                times=datetimes,
                include_before=False,
                include_after=False,
            ),
        )

        assert np.all(cumulative == np.array([1, 2]))


class TestBooleanTimeSeries:
    @pytest.fixture
    def boolean_series(self):
        return TimeSeriesBoolean(
            values=[False, True, True, False, True, True, False],
            periods=Periods.create_periods(
                times=[
                    datetime(2019, 7, 1),
                    datetime(2020, 1, 1),
                    datetime(2020, 7, 1),
                    datetime(2021, 1, 1),
                    datetime(2021, 7, 1),
                    datetime(2022, 1, 1),
                    datetime(2022, 7, 1),
                    datetime(2023, 1, 1),
                ],
                include_before=False,
                include_after=False,
            ),
            unit=Unit.NONE,
        )

    @pytest.fixture
    def two_first_timesteps(self, boolean_series):
        return TimeSeriesBoolean(
            values=boolean_series.values[0:2],
            periods=Periods(boolean_series.periods.periods[0:2]),
            unit=boolean_series.unit,
        )

    def test_resample_boolean(self, boolean_series):
        # resample including start and end date
        yearly_values = boolean_series.resample(freq=Frequency.YEAR)
        assert yearly_values.values == [False, True, False, False]
        assert yearly_values.all_dates == [
            datetime(2019, 7, 1),
            datetime(2020, 1, 1),
            datetime(2021, 1, 1),
            datetime(2022, 1, 1),
            datetime(2023, 1, 1),
        ]

        # resample including start and without end date
        yearly_values = boolean_series.resample(freq=Frequency.YEAR, include_end_date=False)
        assert yearly_values.values == [False, True, False]
        assert yearly_values.all_dates == [
            datetime(2019, 7, 1),
            datetime(2020, 1, 1),
            datetime(2021, 1, 1),
            datetime(2022, 1, 1),
        ]

        # resample without start and including end date
        yearly_values = boolean_series.resample(freq=Frequency.YEAR, include_start_date=False)
        assert yearly_values.values == [True, False, False]
        assert yearly_values.all_dates == [
            datetime(2020, 1, 1),
            datetime(2021, 1, 1),
            datetime(2022, 1, 1),
            datetime(2023, 1, 1),
        ]

        # resample without start and end date
        yearly_values = boolean_series.resample(freq=Frequency.YEAR, include_start_date=False, include_end_date=False)
        assert yearly_values.values == [True, False]
        assert yearly_values.all_dates == [
            datetime(2020, 1, 1),
            datetime(2021, 1, 1),
            datetime(2022, 1, 1),
        ]

    def test_indexing(self, boolean_series):
        first_timestep = TimeSeriesBoolean(
            values=[boolean_series.values[0]],
            periods=Periods([boolean_series.periods.periods[0]]),
            unit=boolean_series.unit,
        )
        assert boolean_series[0] == first_timestep

    def test_slice_indexing(self, boolean_series, two_first_timesteps):
        assert boolean_series[0:2] == two_first_timesteps

    def test_list_indexing(self, boolean_series, two_first_timesteps):
        assert boolean_series[[0, 1]] == two_first_timesteps

    def test_update_single_value(self, boolean_series):
        boolean_series[0] = False
        assert boolean_series.values[0] == False  # noqa: E712, for readability of test

    def test_update_slice(self, boolean_series):
        boolean_series[0:2] = [False, False]
        assert boolean_series.values[0:2] == [False, False]

    def test_update_list_of_indices(self, boolean_series):
        boolean_series[[0, 1]] = [False, False]
        assert boolean_series.values[0:2] == [False, False]

    @pytest.mark.parametrize("left,right", [([1, 2, 3], [1, 2, 3]), ([np.nan], [np.nan]), ([0], [0])])
    def test_equal_comparison(self, boolean_series, left, right):
        left_series = boolean_series.values = left
        right_series = boolean_series.values = right
        assert left_series == right_series

    @pytest.mark.parametrize("left,right", [([1, 2, 3], [1, np.nan, 3]), ([0], [np.nan]), ([1, 2], [1])])
    def test_unequal_comparison(self, boolean_series, left, right):
        left_series = boolean_series.values = left
        right_series = boolean_series.values = right
        assert left_series != right_series


class TestTimeSeriesVolumesCumulative:
    def test_resample_upsampling(self):
        rates = TimeSeriesVolumesCumulative(
            periods=Periods.create_periods(
                times=[
                    datetime(2023, 1, 1),
                    datetime(2024, 1, 1),
                    datetime(2025, 1, 1),
                    datetime(2026, 1, 1),
                ],
                include_before=False,
                include_after=False,
            ),
            values=[1, 2, 3],
            unit=Unit.KILO,
        )

        rates_monthly = rates.resample(freq=Frequency.MONTH)
        assert len(rates_monthly) == 3 * 12
        assert rates_monthly.values[11::12] == [1, 2, 3]  # Ensure original data every 12th month is preserved.

    def test_resample_down_sampling(self):
        """We do not expect to be able to reproduce the cumulative values when down-sampling. This is simply because
        we lose information. The current implementation does not calculate the weighted average of the down-sampled
        period.
        """
        rates = TimeSeriesVolumesCumulative(
            periods=Periods.create_periods(
                times=[
                    datetime(2023, 1, 1),
                    datetime(2023, 4, 1),
                    datetime(2023, 7, 1),
                    datetime(2023, 10, 1),
                    datetime(2024, 1, 1),
                    datetime(2024, 4, 1),
                    datetime(2024, 7, 1),
                    datetime(2024, 10, 1),
                ],
                include_before=False,
                include_after=False,
            ),
            values=[1, 2, 3, 4, 5, 6, 7],
            unit=Unit.KILO,
        )
        rates_yearly = rates.resample(freq=Frequency.YEAR, include_end_date=False)
        assert rates_yearly.values == [4]
        rates_yearly = rates.resample(freq=Frequency.YEAR, include_end_date=True)
        assert rates_yearly.values == [4, 7]


class TestTimeSeriesVolumesResample:
    def test_resample(self):
        volumes = TimeSeriesVolumes(
            periods=Periods.create_periods(
                times=[
                    datetime(2022, 1, 1),
                    datetime(2022, 6, 1),
                    datetime(2023, 1, 1),
                    datetime(2023, 6, 1),
                    datetime(2024, 1, 1),
                    datetime(2024, 6, 1),
                    datetime(2025, 1, 1),
                ],
                include_before=False,
                include_after=False,
            ),
            values=[1, 2, 3, 4, 5, 6],
            unit=Unit.KILO_PER_DAY,
        )

        resampled_volumes = volumes.resample(freq=Frequency.YEAR)
        assert resampled_volumes.all_dates == [
            datetime(2022, 1, 1),
            datetime(2023, 1, 1),
            datetime(2024, 1, 1),
            datetime(2025, 1, 1),
        ]
        assert resampled_volumes.values == [3, 7, 11]

    def test_resample_missing_year(self):
        volumes = TimeSeriesVolumes(
            periods=Periods.create_periods(
                times=[
                    datetime(2022, 1, 1),
                    datetime(2022, 6, 1),
                    datetime(2023, 2, 1),
                    datetime(2023, 6, 1),
                    datetime(2024, 1, 1),
                    datetime(2024, 6, 1),
                    datetime(2025, 1, 1),
                ],
                include_before=False,
                include_after=False,
            ),
            values=[1, 2, 3, 4, 5, 6],
            unit=Unit.KILO_PER_DAY,
        )

        resampled_volumes = volumes.resample(freq=Frequency.YEAR)

        assert resampled_volumes.values == pytest.approx([2.75, 7.25, 11.0], 0.01)


class TestTimeSeriesRate:
    def test_none_value_timeseriesrate(self):
        rate1 = TimeSeriesRate(
            periods=Periods(
                [
                    Period(
                        start=datetime(2023, 1, 1),
                        end=datetime(2023, 6, 1),
                    )
                ]
            ),
            values=[10] * 1,
            regularity=[None],
            unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
            rate_type=RateType.STREAM_DAY,
        )

        assert np.isnan(rate1.regularity)

    def test_adding_timeseriesrate(self):
        rate1 = TimeSeriesRate(
            periods=Periods.create_periods(
                times=[
                    datetime(2023, 1, 1),
                    datetime(2023, 1, 4),
                    datetime(2023, 1, 7),
                    datetime(2023, 1, 9),
                ],
                include_before=False,
                include_after=False,
            ),
            values=[10] * 3,
            regularity=[1, 0.9, 0.5],
            unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
            rate_type=RateType.STREAM_DAY,
        )
        rate2 = TimeSeriesRate(
            periods=Periods.create_periods(
                times=[
                    datetime(2023, 1, 1),
                    datetime(2023, 1, 4),
                    datetime(2023, 1, 7),
                    datetime(2023, 1, 9),
                ],
                include_before=False,
                include_after=False,
            ),
            values=[10] * 3,
            regularity=[1.0, 0.9, 0.5],
            unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
            rate_type=RateType.STREAM_DAY,
        )

        expected_values = [20] * 3  # all values are 10
        expected_regularity = [
            (regularity1 + regularity2) / 2 for regularity1, regularity2 in zip(rate1.regularity, rate2.regularity)
        ]

        sum_of_rates = rate1 + rate2

        assert sum_of_rates.values == expected_values
        assert sum_of_rates.regularity == expected_regularity

    def test_mismatch_timesteps_values(self):
        with pytest.raises(ValidationError) as exc_info:
            TimeSeriesRate(
                periods=Periods.create_periods(
                    times=[
                        datetime(2023, 1, 1),
                        datetime(2023, 1, 4),
                        datetime(2023, 1, 7),
                        datetime(2023, 1, 9),
                    ],
                    include_before=False,
                    include_after=False,
                ),
                values=[10] * 4,
                regularity=[1, 1, 1],
                unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                rate_type=RateType.STREAM_DAY,
            )

        assert (
            "Time series: "
            "number of periods do not match number of values. "
            "Most likely a bug, report to eCalc Dev Team."
        ) in str(exc_info.value)

    def test_mismatch_regularity_values(self):
        with pytest.raises(ValidationError) as exc_info:
            TimeSeriesRate(
                periods=Periods.create_periods(
                    times=[
                        datetime(2023, 1, 1),
                        datetime(2023, 1, 4),
                        datetime(2023, 1, 7),
                        datetime(2023, 1, 9),
                    ],
                    include_before=False,
                    include_after=False,
                ),
                values=[10] * 3,
                regularity=[1, 1, 1, 1],
                unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
                rate_type=RateType.STREAM_DAY,
            )

        assert (
            "Regularity must correspond to nr of periods. Length of periods (3) !=  length of regularity (4)."
            in str(exc_info.value)
        )

    def test_for_period(self):
        rate = TimeSeriesRate(
            periods=Periods.create_periods(
                times=[
                    datetime(2023, 1, 1),
                    datetime(2023, 1, 4),
                    datetime(2023, 1, 7),
                    datetime(2023, 1, 9),
                ],
                include_before=False,
                include_after=False,
            ),
            values=[3, 4, 5],
            unit=Unit.KILO_PER_DAY,
            rate_type=RateType.STREAM_DAY,
            regularity=[1.0] * 3,
        )

        first_period = rate.for_period(rate.periods.periods[0])
        assert first_period.values == [3]
        assert first_period.periods.periods[0].start == datetime(2023, 1, 1)
        assert first_period.periods.periods[0].end == datetime(2023, 1, 4)

        second_period = rate.for_period(rate.periods.periods[1])
        assert second_period.values == [4]
        assert second_period.periods.periods[0].start == datetime(2023, 1, 4)
        assert second_period.periods.periods[0].end == datetime(2023, 1, 7)

        third_period = rate.for_period(rate.periods.periods[2])
        assert third_period.values == [5]
        assert third_period.periods.periods[0].start == datetime(2023, 1, 7)
        assert third_period.periods.periods[0].end == datetime(2023, 1, 9)


class TestTimeseriesRateToVolumes:
    def test_to_volumes(self):
        rates = TimeSeriesRate(
            periods=Periods.create_periods(
                times=[
                    datetime(2023, 1, 1),
                    datetime(2023, 1, 4),
                    datetime(2023, 1, 7),
                    datetime(2023, 1, 9),
                ],
                include_before=False,
                include_after=False,
            ),
            values=[3, 4, 5],
            unit=Unit.KILO_PER_DAY,
            rate_type=RateType.STREAM_DAY,
            regularity=[1.0] * 3,
        )
        volumes = rates.to_volumes()
        assert volumes.values == [9, 12, 10]
        assert volumes.all_dates == [
            datetime(2023, 1, 1),
            datetime(2023, 1, 4),
            datetime(2023, 1, 7),
            datetime(2023, 1, 9),
        ]

    def test_resample_up_sampling(self):
        """We expect up-sampling to be able to reproduce cumulative volumes."""
        rates = TimeSeriesRate(
            periods=Periods.create_periods(
                times=[
                    datetime(2023, 1, 1),
                    datetime(2024, 1, 1),
                    datetime(2025, 1, 1),
                    datetime(2026, 1, 1),
                ],
                include_before=False,
                include_after=False,
            ),
            values=[1, 2, 3],
            unit=Unit.KILO_PER_DAY,
            rate_type=RateType.CALENDAR_DAY,
            regularity=[1.0] * 3,
        )

        rates_monthly = rates.resample(freq=Frequency.MONTH)
        assert len(rates_monthly) == 3 * 12

        # Check that the final cumulative sum is still the same for both.
        cumulative = np.cumsum(rates.to_volumes().values)
        cumulative_resampled = np.cumsum(rates_monthly.to_volumes().values)

        assert cumulative[-1] == cumulative_resampled[-1]

    def test_resample_down_sampling(self):
        """
        We do not expect to be able to reproduce the cumulative values when down-sampling, unless we include the start
        and end dates in the resampled time series. If not we are losing information.
        """
        rates = TimeSeriesRate(
            periods=Periods.create_periods(
                times=[
                    datetime(2022, 10, 1),
                    datetime(2023, 1, 1),
                    datetime(2023, 4, 1),
                    datetime(2023, 7, 1),
                    datetime(2023, 10, 1),
                    datetime(2024, 1, 1),
                    datetime(2024, 4, 1),
                    datetime(2024, 7, 1),
                    datetime(2024, 10, 1),
                ],
                include_before=False,
                include_after=False,
            ),
            values=[1, 2, 3, 4, 5, 6, 7, 8],
            unit=Unit.KILO_PER_DAY,
            rate_type=RateType.CALENDAR_DAY,
            regularity=[1.0] * 8,
        )
        rates_yearly_without_start_end = rates.resample(
            freq=Frequency.YEAR, include_start_date=False, include_end_date=False
        )
        rates_yearly_without_start = rates.resample(freq=Frequency.YEAR, include_start_date=False)
        rates_yearly_without_end = rates.resample(freq=Frequency.YEAR, include_end_date=False)
        rates_yearly = rates.resample(freq=Frequency.YEAR)

        # now with average rates in the new sampling period
        assert np.allclose(rates_yearly_without_start_end.values, [3.509589], rtol=1e-3)
        assert np.allclose(rates_yearly_without_start.values, [3.509589, 7.003650], rtol=1e-3)
        assert np.allclose(rates_yearly_without_end.values, [1, 3.509589], rtol=1e-3)
        assert np.allclose(rates_yearly.values, [1, 3.509589, 7.003650], rtol=1e-3)

        cumulative = np.cumsum(rates.to_volumes().values)
        cumulative_resampled_without_start_end = np.cumsum(rates_yearly_without_start_end.to_volumes().values)
        cumulative_resampled_without_start = np.cumsum(rates_yearly_without_start.to_volumes().values)
        cumulative_resampled_without_end = np.cumsum(rates_yearly_without_end.to_volumes().values)
        cumulative_resampled = np.cumsum(rates_yearly.to_volumes().values)

        assert cumulative[-1] == cumulative_resampled[-1]
        assert cumulative[-1] > cumulative_resampled_without_start_end[-1]  # losing volumes at the start and end
        assert cumulative[-1] > cumulative_resampled_without_start[-1]  # losing volumes at the start
        assert cumulative[-1] > cumulative_resampled_without_end[-1]  # losing volumes at the end

    def test_resample_up_and_down_sampling(self):
        """If the start and end dates are included, both monthly and yearly resampling should reproduce the cumulative
        volumes. If the end date is excluded, the yearly resampling should lose more information/volumes than the
        monthly resampling"""
        rates = TimeSeriesRate(
            periods=Periods.create_periods(
                times=[
                    datetime(2023, 1, 1),
                    datetime(2023, 1, 7),
                    datetime(2023, 1, 14),
                    datetime(2023, 4, 1),
                    datetime(2023, 7, 1),
                    datetime(2023, 10, 1),
                    datetime(2024, 2, 2),
                ],
                include_before=False,
                include_after=False,
            ),
            values=[1, 2, 3, 4, 5, 6],
            unit=Unit.KILO_PER_DAY,
            rate_type=RateType.CALENDAR_DAY,
            regularity=[1.0] * 6,
        )
        rates_monthly = rates.resample(freq=Frequency.MONTH)
        rates_yearly = rates.resample(freq=Frequency.YEAR)
        rates_monthly_without_end = rates.resample(freq=Frequency.MONTH, include_end_date=False)
        rates_yearly_without_end = rates.resample(freq=Frequency.YEAR, include_end_date=False)
        assert np.allclose(
            rates_monthly.values,
            [2.387097, 3.0, 3.0, 4.0, 4.0, 4.0, 5.0, 5.0, 5.0, 6.0, 6.0, 6.0, 6.0, 6.0],
        )
        assert np.allclose(rates_yearly.values, [4.45753424, 6.0])
        cumulative = np.cumsum(rates.to_volumes().values)
        cumulative_monthly = np.cumsum(rates_monthly.to_volumes().values)
        cumulative_yearly = np.cumsum(rates_yearly.to_volumes().values)
        assert cumulative[-1] == cumulative_monthly[-1] == cumulative_yearly[-1]
        assert np.allclose(cumulative_monthly[11], cumulative_yearly[0])

        assert np.allclose(
            rates_monthly_without_end.values,
            [2.387097, 3.0, 3.0, 4.0, 4.0, 4.0, 5.0, 5.0, 5.0, 6.0, 6.0, 6.0, 6.0],
        )
        assert np.allclose(rates_yearly_without_end.values, [4.45753424])
        cumulative_monthly_without_end = np.cumsum(rates_monthly_without_end.to_volumes().values)
        cumulative_yearly_without_end = np.cumsum(rates_yearly_without_end.to_volumes().values)

        assert cumulative[-1] > cumulative_monthly_without_end[-1] > cumulative_yearly_without_end[-1]
        assert np.allclose(cumulative_monthly[11], cumulative_yearly[0])


class TestTimeSeriesFloat:
    def test_resample_down_sampling(self):
        rates = TimeSeriesFloat(
            periods=Periods.create_periods(
                times=[
                    datetime(2023, 1, 1),
                    datetime(2023, 7, 1),
                    datetime(2023, 9, 1),
                    datetime(2023, 11, 1),
                    datetime(2024, 1, 1),
                    datetime(2025, 1, 1),
                ],
                include_before=False,
                include_after=False,
            ),
            values=[10, 20, 0, 2, 30],
            unit=Unit.BARA,
        )

        rates_yearly = rates.resample(freq=Frequency.YEAR)
        assert np.allclose(rates_yearly.values, [10, 30])

    def test_resample_up_sampling(self):
        rates = TimeSeriesFloat(
            periods=Periods.create_periods(
                times=[datetime(2023, 1, 1), datetime(2024, 1, 1), datetime(2025, 1, 1)],
                include_before=False,
                include_after=False,
            ),
            values=[10, 20],
            unit=Unit.BARA,
        )

        rates_monthly = rates.resample(freq=Frequency.MONTH)
        assert len(rates_monthly) == 2 * 12  # Including January 2025.
        assert rates_monthly.values[::12] == [10, 20]


class TestTimeSeriesMerge:
    def test_merge_time_series_float_overlapping_periods(self):
        """
        Use TimeSeriesFloat to test the 'generic' merge (parent class merge)
        """

        first = TimeSeriesFloat(
            periods=Periods.create_periods(
                times=[
                    datetime(2021, 1, 1),
                    datetime(2023, 1, 1),
                ],
                include_before=False,
                include_after=False,
            ),
            values=[11],
            unit=Unit.TONS,
        )

        second = TimeSeriesFloat(
            periods=Periods.create_periods(
                times=[
                    datetime(2020, 1, 1),
                    datetime(2022, 1, 1),
                    datetime(2024, 1, 1),
                    datetime(2030, 1, 1),
                ],
                include_before=False,
                include_after=False,
            ),
            values=[21, 22, 23],
            unit=Unit.TONS,
        )

        with pytest.raises(ValueError) as exc_info:
            first.merge(second)

        assert str(exc_info.value) == "Can not merge two TimeSeries with overlapping periods."

    def test_merge_time_series_float_gap_between_periods(self):
        """
        Use TimeSeriesFloat to test the 'generic' merge (parent class merge)
        """

        first = TimeSeriesFloat(
            periods=Periods.create_periods(
                times=[
                    datetime(2021, 1, 1),
                    datetime(2022, 1, 1),
                ],
                include_before=False,
                include_after=False,
            ),
            values=[11],
            unit=Unit.TONS,
        )

        second = TimeSeriesFloat(
            periods=Periods.create_periods(
                times=[
                    datetime(2023, 1, 1),
                    datetime(2024, 1, 1),
                    datetime(2025, 1, 1),
                    datetime(2026, 1, 1),
                ],
                include_before=False,
                include_after=False,
            ),
            values=[21, 22, 23],
            unit=Unit.TONS,
        )

        with pytest.raises(ValueError) as exc_info:
            first.merge(second)

        assert str(exc_info.value) == "Can not merge two TimeSeries when there is a gap in time between them."

    def test_merge_time_series_float_different_unit(self):
        first = TimeSeriesFloat(
            periods=Periods.create_periods(
                times=[
                    datetime(2021, 1, 1),
                    datetime(2022, 1, 1),
                ],
                include_before=False,
                include_after=False,
            ),
            values=[11],
            unit=Unit.TONS,
        )

        second = TimeSeriesFloat(
            periods=Periods.create_periods(
                times=[
                    datetime(2020, 1, 1),
                    datetime(2022, 1, 1),
                ],
                include_before=False,
                include_after=False,
            ),
            values=[21],
            unit=Unit.TONS_PER_DAY,
        )

        with pytest.raises(ValueError) as exc_info:
            first.merge(second)

        assert str(exc_info.value) == "Mismatching units: 't' != 't/d'"

    def test_merge_time_series_float_overlapping_timesteps(self):
        first = TimeSeriesFloat(
            periods=Periods.create_periods(
                times=[
                    datetime(2020, 1, 1),
                    datetime(2021, 1, 1),
                ],
                include_before=False,
                include_after=False,
            ),
            values=[11],
            unit=Unit.TONS,
        )

        second = TimeSeriesFloat(
            periods=Periods.create_periods(
                times=[datetime(2021, 1, 1), datetime(2022, 1, 1)],
                include_before=False,
                include_after=False,
            ),
            values=[21],
            unit=Unit.TONS,
        )

        assert first.merge(second) == TimeSeriesFloat(
            periods=Periods.create_periods(
                times=[
                    datetime(2020, 1, 1),
                    datetime(2021, 1, 1),
                    datetime(2022, 1, 1),
                ],
                include_before=False,
                include_after=False,
            ),
            values=[11, 21],
            unit=Unit.TONS,
        )

    def test_merge_time_series_different_types(self):
        first = TimeSeriesFloat(
            periods=Periods.create_periods(
                times=[
                    datetime(2021, 1, 1),
                    datetime(2022, 1, 1),
                ],
                include_before=False,
                include_after=False,
            ),
            values=[11],
            unit=Unit.TONS,
        )

        second = TimeSeriesBoolean(
            periods=Periods.create_periods(
                times=[
                    datetime(2021, 1, 1),
                    datetime(2022, 1, 1),
                ],
                include_before=False,
                include_after=False,
            ),
            values=[True],
            unit=Unit.TONS,
        )

        with pytest.raises(ValueError) as exc_info:
            first.merge(second)

        assert str(exc_info.value) == (
            "Can not merge <class 'libecalc.common.utils.rates.TimeSeriesFloat'> with "
            "<class 'libecalc.common.utils.rates.TimeSeriesBoolean'>"
        )

    def test_merge_time_series_rate_success(self):
        """
        Use TimeSeriesFloat to test the 'generic' merge (parent class merge)
        """

        first = TimeSeriesRate(
            periods=Periods.create_periods(
                times=[
                    datetime(2020, 1, 1),
                    datetime(2021, 1, 1),
                ],
                include_before=False,
                include_after=False,
            ),
            values=[11],
            unit=Unit.TONS,
            regularity=[1],
            rate_type=RateType.STREAM_DAY,
        )

        second = TimeSeriesRate(
            periods=Periods.create_periods(
                times=[
                    datetime(2021, 1, 1),
                    datetime(2022, 1, 1),
                    datetime(2023, 1, 1),
                    datetime(2024, 1, 1),
                    datetime(2025, 1, 1),
                    datetime(2026, 1, 1),
                ],
                include_before=False,
                include_after=False,
            ),
            values=[21, 22, 23, 24, 25],
            unit=Unit.TONS,
            regularity=[1, 0.8, 0.6, 0.4, 0.2],
            rate_type=RateType.STREAM_DAY,
        )

        assert first.merge(second) == TimeSeriesRate(
            periods=Periods.create_periods(
                times=[
                    datetime(2020, 1, 1),
                    datetime(2021, 1, 1),
                    datetime(2022, 1, 1),
                    datetime(2023, 1, 1),
                    datetime(2024, 1, 1),
                    datetime(2025, 1, 1),
                    datetime(2026, 1, 1),
                ],
                include_before=False,
                include_after=False,
            ),
            values=[11, 21, 22, 23, 24, 25],
            unit=Unit.TONS,
            regularity=[1, 1, 0.8, 0.6, 0.4, 0.2],
            rate_type=RateType.STREAM_DAY,
        )

    def test_merge_time_series_rate_different_unit(self):
        first = TimeSeriesRate(
            periods=Periods.create_periods(
                times=[
                    datetime(2020, 1, 1),
                    datetime(2021, 1, 1),
                ],
                include_before=False,
                include_after=False,
            ),
            values=[11],
            unit=Unit.TONS,
            rate_type=RateType.CALENDAR_DAY,
            regularity=[1.0],
        )

        second = TimeSeriesRate(
            periods=Periods.create_periods(
                times=[
                    datetime(2021, 1, 1),
                    datetime(2022, 1, 1),
                ],
                include_before=False,
                include_after=False,
            ),
            values=[21],
            unit=Unit.TONS_PER_DAY,
            rate_type=RateType.CALENDAR_DAY,
            regularity=[1.0],
        )

        with pytest.raises(ValueError) as exc_info:
            first.merge(second)

        assert str(exc_info.value) == "Mismatching units: 't' != 't/d'"

    def test_merge_time_series_rate_overlapping_periods(self):
        first = TimeSeriesRate(
            periods=Periods.create_periods(
                times=[
                    datetime(2020, 1, 1),
                    datetime(2021, 1, 1),
                ],
                include_before=False,
                include_after=False,
            ),
            values=[11],
            unit=Unit.TONS,
            rate_type=RateType.CALENDAR_DAY,
            regularity=[1.0],
        )

        second = TimeSeriesRate(
            periods=Periods.create_periods(
                times=[
                    datetime(2020, 8, 1),
                    datetime(2022, 1, 1),
                ],
                include_before=False,
                include_after=False,
            ),
            values=[21],
            unit=Unit.TONS,
            rate_type=RateType.CALENDAR_DAY,
            regularity=[1.0],
        )

        with pytest.raises(ValueError) as exc_info:
            first.merge(second)

        assert str(exc_info.value) == "Can not merge two TimeSeries with overlapping periods"

    def test_merge_time_series_rate_different_types(self):
        first = TimeSeriesRate(
            periods=Periods.create_periods(
                times=[
                    datetime(2020, 1, 1),
                    datetime(2021, 1, 1),
                ],
                include_before=False,
                include_after=False,
            ),
            values=[11],
            unit=Unit.TONS,
            rate_type=RateType.CALENDAR_DAY,
            regularity=[1.0],
        )

        second = TimeSeriesBoolean(
            periods=Periods.create_periods(
                times=[
                    datetime(2020, 1, 1),
                    datetime(2021, 1, 1),
                ],
                include_before=False,
                include_after=False,
            ),
            values=[True],
            unit=Unit.TONS,
        )

        with pytest.raises(ValueError) as exc_info:
            first.merge(second)

        assert str(exc_info.value) == (
            "Can not merge <class 'libecalc.common.utils.rates.TimeSeriesRate'> with "
            "<class 'libecalc.common.utils.rates.TimeSeriesBoolean'>"
        )

    def test_merge_time_series_rate_different_rate_types(self):
        first = TimeSeriesRate(
            periods=Periods.create_periods(
                times=[
                    datetime(2020, 1, 1),
                    datetime(2021, 1, 1),
                ],
                include_before=False,
                include_after=False,
            ),
            values=[11],
            unit=Unit.TONS,
            rate_type=RateType.CALENDAR_DAY,
            regularity=[1.0],
        )

        second = TimeSeriesRate(
            periods=Periods.create_periods(
                times=[
                    datetime(2021, 1, 1),
                    datetime(2022, 1, 1),
                ],
                include_before=False,
                include_after=False,
            ),
            values=[11],
            unit=Unit.TONS,
            rate_type=RateType.STREAM_DAY,
            regularity=[1.0],
        )

        with pytest.raises(ValueError) as exc_info:
            first.merge(second)

        assert str(exc_info.value) == (
            "Mismatching rate type. Currently you can not merge stream/calendar day rates "
            "with calendar/stream day rates."
        )
