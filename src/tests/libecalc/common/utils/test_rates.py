from datetime import datetime

import numpy as np
import pytest
from libecalc.common.time_utils import Frequency
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    Rates,
    TimeSeriesBoolean,
    TimeSeriesFloat,
    TimeSeriesRate,
    TimeSeriesVolumes,
    TimeSeriesVolumesCumulative,
)
from libecalc.dto.types import RateType


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
            np.array([1, 1, 1, 1, 1]), np.array([datetime(2000, 1, n) for n in range(1, 6)])
        )
        assert cumulative[0] == 0  # First should always be zero.
        assert cumulative.tolist() == [0, 1, 2, 3, 4]

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
        rates = np.array([1, 1.5, 1.5, 2, 1, 1.3, 1])
        output = Rates.compute_cumulative_volumes_from_daily_rates(rates, time_steps=time_steps)
        assert output.tolist() == [0.0, 1.0, 4.0, 5.5, 11.5, 16.5, 17.8]

    def test_compute_cumulative_from_rates_and_delta_time_simple_data(self):
        # 3 consecutive days [2022.01.01, 2022.01.03];
        datetimes = np.array(
            [
                datetime(year=2022, month=1, day=1),
                datetime(year=2022, month=1, day=2),
                datetime(year=2022, month=1, day=3),
            ]
        )

        # 1 per day
        rate_vector = [1, 1]

        cumulative = Rates.compute_cumulative_volumes_from_daily_rates(rate_vector, time_steps=datetimes)

        # the first interval is always 0, it is manually added to get same length of arrays for further usage...
        assert np.all(cumulative == np.array([0, 1, 2]))


class TestBooleanTimeSeries:
    @pytest.fixture
    def boolean_series(self):
        return TimeSeriesBoolean(
            values=[True, True, False, True],
            timesteps=[
                datetime(2020, 1, 1),
                datetime(2020, 7, 1),
                datetime(2021, 1, 1),
                datetime(2021, 7, 1),
            ],
            unit=Unit.NONE,
        )

    @pytest.fixture
    def two_first_timesteps(self, boolean_series):
        return TimeSeriesBoolean(
            values=boolean_series.values[0:2], timesteps=boolean_series.timesteps[0:2], unit=boolean_series.unit
        )

    def test_resample_boolean(self, boolean_series):
        yearly_values = boolean_series.resample(freq=Frequency.YEAR)
        assert yearly_values.values == [True, False]
        assert yearly_values.timesteps == [datetime(2020, 1, 1), datetime(2021, 1, 1)]

    def test_indexing(self, boolean_series):
        first_timestep = TimeSeriesBoolean(
            values=[boolean_series.values[0]], timesteps=[boolean_series.timesteps[0]], unit=boolean_series.unit
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
            timesteps=[
                datetime(2023, 1, 1),
                datetime(2024, 1, 1),
                datetime(2025, 1, 1),
                datetime(2026, 1, 1),
            ],
            values=[1, 2, 3, 4],
            unit=Unit.KILO,
        )

        rates_monthly = rates.resample(freq=Frequency.MONTH)
        assert len(rates_monthly) == 3 * 12 + 1  # Including January 2026.
        assert rates_monthly.values[::12] == [1, 2, 3, 4]  # Ensure original data every 12th month is preserved.

    def test_resample_down_sampling(self):
        """We do not expect to be able to reproduce the cumulative values when down-sampling. This is simply because
        we lose information. The current implementation does not calculate the weighted average of the down-sampled
        period.
        """
        rates = TimeSeriesVolumesCumulative(
            timesteps=[
                datetime(2023, 1, 1),
                datetime(2023, 4, 1),
                datetime(2023, 7, 1),
                datetime(2023, 10, 1),
                datetime(2024, 1, 1),
                datetime(2024, 4, 1),
                datetime(2024, 7, 1),
                datetime(2024, 10, 1),
            ],
            values=[1, 2, 3, 4, 5, 6, 7, 8],
            unit=Unit.KILO,
        )
        rates_yearly = rates.resample(freq=Frequency.YEAR)
        assert rates_yearly.values == [1, 5]


class TestTimeSeriesVolumesReindex:
    def test_reindex(self):
        volumes = TimeSeriesVolumes(
            timesteps=[
                datetime(2022, 1, 1),
                datetime(2022, 6, 1),
                datetime(2023, 1, 1),
                datetime(2023, 6, 1),
                datetime(2024, 1, 1),
                datetime(2024, 6, 1),
                datetime(2025, 1, 1),
            ],
            values=[1, 2, 3, 4, 5, 6],
            unit=Unit.KILO_PER_DAY,
        )

        reindexd_volumes = volumes.reindex(
            time_steps=[
                datetime(2022, 1, 1),
                datetime(2023, 1, 1),
                datetime(2024, 1, 1),
                datetime(2025, 1, 1),
            ]
        )
        assert reindexd_volumes.timesteps == [
            datetime(2022, 1, 1),
            datetime(2023, 1, 1),
            datetime(2024, 1, 1),
        ]
        assert reindexd_volumes.values == [3, 7, 11]

    def test_reindex_missing_year(self):
        volumes = TimeSeriesVolumes(
            timesteps=[
                datetime(2022, 1, 1),
                datetime(2022, 6, 1),
                datetime(2023, 2, 1),
                datetime(2023, 6, 1),
                datetime(2024, 1, 1),
                datetime(2024, 6, 1),
                datetime(2025, 1, 1),
            ],
            values=[1, 2, 3, 4, 5, 6],
            unit=Unit.KILO_PER_DAY,
        )

        with pytest.raises(ValueError) as exc_info:
            _ = volumes.reindex(
                time_steps=[
                    datetime(2022, 1, 1),
                    datetime(2023, 1, 1),
                    datetime(2024, 1, 1),
                    datetime(2025, 1, 1),
                ],
            )

        assert str(exc_info.value) == "Could not reindex volumes. Missing time step `2023-01-01 00:00:00`."

    def test_reindex_with_extrapolation(self):
        volumes = TimeSeriesVolumes(
            timesteps=[
                datetime(2023, 1, 1),
                datetime(2023, 6, 1),
                datetime(2024, 1, 1),
                datetime(2024, 6, 1),
                datetime(2025, 1, 1),
            ],
            values=[3, 4, 5, 6],
            unit=Unit.KILO_PER_DAY,
        )

        reindexd_volumes = volumes.reindex(
            time_steps=[
                datetime(2022, 1, 1),
                datetime(2023, 1, 1),
                datetime(2024, 1, 1),
                datetime(2025, 1, 1),
            ]
        )
        assert reindexd_volumes.timesteps == [
            datetime(2022, 1, 1),
            datetime(2023, 1, 1),
            datetime(2024, 1, 1),
        ]
        np.testing.assert_allclose(reindexd_volumes.values, [np.nan, 7, 11])


class TestTimeSeriesRate:
    def test_adding_timeseriesrate(self):
        rate1 = TimeSeriesRate(
            timesteps=[
                datetime(2023, 1, 1),
                datetime(2023, 1, 4),
                datetime(2023, 1, 7),
                datetime(2023, 1, 9),
            ],
            values=[10] * 4,
            regularity=[1, 0.9, 0.5, 0.0],
            unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
            rate_type=RateType.STREAM_DAY,
        )
        rate2 = TimeSeriesRate(
            timesteps=[
                datetime(2023, 1, 1),
                datetime(2023, 1, 4),
                datetime(2023, 1, 7),
                datetime(2023, 1, 9),
            ],
            values=[10] * 4,
            regularity=[1.0, 0.9, 0.5, 0.0],
            unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
            rate_type=RateType.STREAM_DAY,
        )

        expected_values = [20] * 4  # all values are 10
        expected_regularity = [
            (regularity1 + regularity2) / 2 for regularity1, regularity2 in zip(rate1.regularity, rate2.regularity)
        ]

        sum_of_rates = rate1 + rate2

        assert sum_of_rates.values == expected_values
        assert sum_of_rates.regularity == expected_regularity


class TestTimeseriesRateToVolumes:
    def test_to_volumes(self):
        rates = TimeSeriesRate(
            timesteps=[
                datetime(2023, 1, 1),
                datetime(2023, 1, 4),
                datetime(2023, 1, 7),
                datetime(2023, 1, 9),
            ],
            values=[3, 4, 5, 6],
            unit=Unit.KILO_PER_DAY,
            rate_type=RateType.STREAM_DAY,
            regularity=[1.0] * 4,
        )
        volumes = rates.to_volumes()
        assert volumes.values == [9, 12, 10]
        assert volumes.timesteps == [
            datetime(2023, 1, 1),
            datetime(2023, 1, 4),
            datetime(2023, 1, 7),
            datetime(2023, 1, 9),
        ]

    def test_resample_up_sampling(self):
        """We expect up-sampling to be able to reproduce cumulative volumes."""
        rates = TimeSeriesRate(
            timesteps=[
                datetime(2023, 1, 1),
                datetime(2024, 1, 1),
                datetime(2025, 1, 1),
                datetime(2026, 1, 1),
            ],
            values=[1, 2, 3, 4],
            unit=Unit.KILO_PER_DAY,
            rate_type=RateType.CALENDAR_DAY,
            regularity=[1.0] * 4,
        )

        rates_monthly = rates.resample(freq=Frequency.MONTH)
        assert len(rates_monthly) == 3 * 12 + 1  # Including January 2026.

        # Check that the final cumulative sum is still the same for both.
        cumulative = np.cumsum(rates.to_volumes().values)
        cumulative_resampled = np.cumsum(rates_monthly.to_volumes().values)

        assert cumulative[-1] == cumulative_resampled[-1]

    def test_resample_down_sampling(self):
        """
        We do not expect to be able to reproduce the cumulative values when down-sampling, unless the last date
        coincides with a date with the chosen frequency. This is simply because we lose information.
        """
        rates = TimeSeriesRate(
            timesteps=[
                datetime(2023, 1, 1),
                datetime(2023, 4, 1),
                datetime(2023, 7, 1),
                datetime(2023, 10, 1),
                datetime(2024, 1, 1),
                datetime(2024, 4, 1),
                datetime(2024, 7, 1),
                datetime(2024, 10, 1),
            ],
            values=[1, 2, 3, 4, 5, 6, 7, 8],
            unit=Unit.KILO_PER_DAY,
            rate_type=RateType.CALENDAR_DAY,
            regularity=[1.0] * 8,
        )
        rates_yearly = rates.resample(freq=Frequency.YEAR)
        # now with average rates in the new sampling period
        assert np.allclose(rates_yearly.values, [2.509589, 0.0], rtol=1e-6)

        cumulative = np.cumsum(rates.to_volumes().values)
        cumulative_resampled = np.cumsum(rates_yearly.to_volumes().values)

        assert cumulative[-1] != cumulative_resampled[-1]

    def test_resample_up_and_down_sampling(self):
        """ """
        rates = TimeSeriesRate(
            timesteps=[
                datetime(2023, 1, 1),
                datetime(2023, 1, 7),
                datetime(2023, 1, 14),
                datetime(2023, 4, 1),
                datetime(2023, 7, 1),
                datetime(2023, 10, 1),
                datetime(2024, 2, 2),
            ],
            values=[1, 2, 3, 4, 5, 6, 7],
            unit=Unit.KILO_PER_DAY,
            rate_type=RateType.CALENDAR_DAY,
            regularity=[1.0] * 7,
        )
        rates_monthly = rates.resample(freq=Frequency.MONTH)
        rates_yearly = rates.resample(freq=Frequency.YEAR)
        assert np.allclose(
            rates_monthly.values, [2.387097, 3.0, 3.0, 4.0, 4.0, 4.0, 5.0, 5.0, 5.0, 6.0, 6.0, 6.0, 6.0, 0.0], rtol=1e-6
        )
        assert np.allclose(rates_yearly.values, [4.45753424, 0.0])
        cumulative = np.cumsum(rates.to_volumes().values)
        cumulative_monthly = np.cumsum(rates_monthly.to_volumes().values)
        cumulative_yearly = np.cumsum(rates_yearly.to_volumes().values)
        assert cumulative[-1] > cumulative_monthly[-1] > cumulative_yearly[-1]
        assert np.allclose(cumulative_monthly[11], cumulative_yearly[0])


class TestTimeSeriesFloat:
    def test_resample_down_sampling(self):
        rates = TimeSeriesFloat(
            timesteps=[
                datetime(2023, 1, 1),
                datetime(2023, 7, 1),
                datetime(2023, 9, 1),
                datetime(2023, 11, 1),
                datetime(2024, 1, 1),
                datetime(2025, 1, 1),
            ],
            values=[10, 20, 0, 2, 30, 40],
            unit=Unit.BARA,
        )

        rates_yearly = rates.resample(freq=Frequency.YEAR)
        assert np.allclose(rates_yearly.values, [10, 30, 40])


def test_resample_up_sampling():
    rates = TimeSeriesFloat(
        timesteps=[datetime(2023, 1, 1), datetime(2024, 1, 1), datetime(2025, 1, 1)],
        values=[10, 20, 30],
        unit=Unit.BARA,
    )

    rates_monthly = rates.resample(freq=Frequency.MONTH)
    assert len(rates_monthly) == 2 * 12 + 1  # Including January 2025.
    assert rates_monthly.values[::12] == [10, 20, 30]


class TestTimeSeriesMerge:
    def test_merge_time_series_float_success(self):
        """
        Use TimeSeriesFloat to test the 'generic' merge (parent class merge)
        """

        first = TimeSeriesFloat(
            timesteps=[datetime(2021, 1, 1), datetime(2023, 1, 1)],
            values=[11, 12],
            unit=Unit.NORWEGIAN_KRONER,
        )

        second = TimeSeriesFloat(
            timesteps=[datetime(2020, 1, 1), datetime(2022, 1, 1), datetime(2024, 1, 1), datetime(2030, 1, 1)],
            values=[21, 22, 23, 24],
            unit=Unit.NORWEGIAN_KRONER,
        )

        assert first.merge(second) == TimeSeriesFloat(
            timesteps=[
                datetime(2020, 1, 1),
                datetime(2021, 1, 1),
                datetime(2022, 1, 1),
                datetime(2023, 1, 1),
                datetime(2024, 1, 1),
                datetime(2030, 1, 1),
            ],
            values=[21, 11, 22, 12, 23, 24],
            unit=Unit.NORWEGIAN_KRONER,
        )

    def test_merge_time_series_float_different_unit(self):
        first = TimeSeriesFloat(
            timesteps=[datetime(2021, 1, 1)],
            values=[11],
            unit=Unit.NORWEGIAN_KRONER,
        )

        second = TimeSeriesFloat(
            timesteps=[datetime(2020, 1, 1)],
            values=[21],
            unit=Unit.NORWEGIAN_KRONER_PER_DAY,
        )

        with pytest.raises(ValueError) as exc_info:
            first.merge(second)

        assert str(exc_info.value) == "Mismatching units: 'NOK' != 'NOK/d'"

    def test_merge_time_series_float_overlapping_timesteps(self):
        first = TimeSeriesFloat(
            timesteps=[datetime(2021, 1, 1)],
            values=[11],
            unit=Unit.NORWEGIAN_KRONER,
        )

        second = TimeSeriesFloat(
            timesteps=[datetime(2020, 1, 1), datetime(2021, 1, 1)],
            values=[21, 22],
            unit=Unit.NORWEGIAN_KRONER,
        )

        with pytest.raises(ValueError) as exc_info:
            first.merge(second)

        assert str(exc_info.value) == "Can not merge two TimeSeries with common timesteps"

    def test_merge_time_series_different_types(self):
        first = TimeSeriesFloat(
            timesteps=[datetime(2021, 1, 1)],
            values=[11],
            unit=Unit.NORWEGIAN_KRONER,
        )

        second = TimeSeriesBoolean(
            timesteps=[datetime(2020, 1, 1)],
            values=[True],
            unit=Unit.NORWEGIAN_KRONER,
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
            timesteps=[datetime(2021, 1, 1), datetime(2023, 1, 1)],
            values=[11, 12],
            unit=Unit.NORWEGIAN_KRONER,
            regularity=[11, 12],
            rate_type=RateType.STREAM_DAY,
        )

        second = TimeSeriesRate(
            timesteps=[datetime(2020, 1, 1), datetime(2022, 1, 1), datetime(2024, 1, 1), datetime(2030, 1, 1)],
            values=[21, 22, 23, 24],
            unit=Unit.NORWEGIAN_KRONER,
            regularity=[21, 22, 23, 24],
            rate_type=RateType.STREAM_DAY,
        )

        assert first.merge(second) == TimeSeriesRate(
            timesteps=[
                datetime(2020, 1, 1),
                datetime(2021, 1, 1),
                datetime(2022, 1, 1),
                datetime(2023, 1, 1),
                datetime(2024, 1, 1),
                datetime(2030, 1, 1),
            ],
            values=[21, 11, 22, 12, 23, 24],
            unit=Unit.NORWEGIAN_KRONER,
            regularity=[21, 11, 22, 12, 23, 24],
            rate_type=RateType.STREAM_DAY,
        )

    def test_merge_time_series_rate_different_unit(self):
        first = TimeSeriesRate(
            timesteps=[datetime(2021, 1, 1)],
            values=[11],
            unit=Unit.NORWEGIAN_KRONER,
            rate_type=RateType.CALENDAR_DAY,
            regularity=[1.0],
        )

        second = TimeSeriesRate(
            timesteps=[datetime(2020, 1, 1)],
            values=[21],
            unit=Unit.NORWEGIAN_KRONER_PER_DAY,
            rate_type=RateType.CALENDAR_DAY,
            regularity=[1.0],
        )

        with pytest.raises(ValueError) as exc_info:
            first.merge(second)

        assert str(exc_info.value) == "Mismatching units: 'NOK' != 'NOK/d'"

    def test_merge_time_series_rate_overlapping_timesteps(self):
        first = TimeSeriesRate(
            timesteps=[datetime(2021, 1, 1)],
            values=[11],
            unit=Unit.NORWEGIAN_KRONER,
            rate_type=RateType.CALENDAR_DAY,
            regularity=[1.0],
        )

        second = TimeSeriesRate(
            timesteps=[datetime(2020, 1, 1), datetime(2021, 1, 1)],
            values=[21, 22],
            unit=Unit.NORWEGIAN_KRONER,
            rate_type=RateType.CALENDAR_DAY,
            regularity=[1.0] * 2,
        )

        with pytest.raises(ValueError) as exc_info:
            first.merge(second)

        assert str(exc_info.value) == "Can not merge two TimeSeries with common timesteps"

    def test_merge_time_series_rate_different_types(self):
        first = TimeSeriesRate(
            timesteps=[datetime(2021, 1, 1)],
            values=[11],
            unit=Unit.NORWEGIAN_KRONER,
            rate_type=RateType.CALENDAR_DAY,
            regularity=[1.0],
        )

        second = TimeSeriesBoolean(
            timesteps=[datetime(2020, 1, 1)],
            values=[True],
            unit=Unit.NORWEGIAN_KRONER,
        )

        with pytest.raises(ValueError) as exc_info:
            first.merge(second)

        assert str(exc_info.value) == (
            "Can not merge <class 'libecalc.common.utils.rates.TimeSeriesRate'> with "
            "<class 'libecalc.common.utils.rates.TimeSeriesBoolean'>"
        )

    def test_merge_time_series_rate_different_rate_types(self):
        first = TimeSeriesRate(
            timesteps=[datetime(2021, 1, 1)],
            values=[11],
            unit=Unit.NORWEGIAN_KRONER_PER_DAY,
            rate_type=RateType.STREAM_DAY,
            regularity=[1.0],
        )

        second = TimeSeriesRate(
            timesteps=[datetime(2020, 1, 1)],
            values=[21],
            unit=Unit.NORWEGIAN_KRONER_PER_DAY,
            rate_type=RateType.CALENDAR_DAY,
            regularity=[1.0],
        )

        with pytest.raises(ValueError) as exc_info:
            first.merge(second)

        assert str(exc_info.value) == (
            "Mismatching rate type. Currently you can not merge stream/calendar day rates "
            "with calendar/stream day rates."
        )
