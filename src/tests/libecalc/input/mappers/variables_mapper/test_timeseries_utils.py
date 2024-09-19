from datetime import datetime

import pytest

import libecalc.common.time_utils
from libecalc.common.time_utils import Frequency
from libecalc.dto.types import InterpolationType
from libecalc.presentation.yaml.domain.time_series import TimeSeries
from libecalc.presentation.yaml.mappers.variables_mapper.get_global_time_vector import (
    _get_end_boundary,
    get_global_time_vector,
)
from libecalc.presentation.yaml.validation_errors import ValidationError


def create_single_date_time_series(interpolation_type: InterpolationType, extrapolate: bool) -> TimeSeries:
    return TimeSeries(
        reference_id="COL1_RATE",
        time_vector=[datetime(2012, 1, 1)],
        series=[3],
        interpolation_type=interpolation_type,
        extrapolate=extrapolate,
    )


class TestGetGlobalTimeVector:
    def test_single_collection(self):
        global_time_vector = get_global_time_vector(
            time_series_time_vector=[
                datetime(2010, 1, 1),
                datetime(2011, 1, 1),
                datetime(2012, 1, 1),
                datetime(2013, 1, 1),
            ],
        )

        assert global_time_vector == [
            datetime(2010, 1, 1),
            datetime(2011, 1, 1),
            datetime(2012, 1, 1),
            datetime(2013, 1, 1),
        ]

    def test_single_collection_with_monthly_frequency(self):
        global_time_vector = get_global_time_vector(
            time_series_time_vector=[
                datetime(2010, 1, 1),
                datetime(2011, 1, 1),
                datetime(2012, 1, 1),
                datetime(2013, 1, 1),
            ],
            frequency=libecalc.common.time_utils.Frequency.MONTH,
        )

        assert global_time_vector == [
            datetime(2010, 1, 1),
            datetime(2010, 2, 1),
            datetime(2010, 3, 1),
            datetime(2010, 4, 1),
            datetime(2010, 5, 1),
            datetime(2010, 6, 1),
            datetime(2010, 7, 1),
            datetime(2010, 8, 1),
            datetime(2010, 9, 1),
            datetime(2010, 10, 1),
            datetime(2010, 11, 1),
            datetime(2010, 12, 1),
            datetime(2011, 1, 1),
            datetime(2011, 2, 1),
            datetime(2011, 3, 1),
            datetime(2011, 4, 1),
            datetime(2011, 5, 1),
            datetime(2011, 6, 1),
            datetime(2011, 7, 1),
            datetime(2011, 8, 1),
            datetime(2011, 9, 1),
            datetime(2011, 10, 1),
            datetime(2011, 11, 1),
            datetime(2011, 12, 1),
            datetime(2012, 1, 1),
            datetime(2012, 2, 1),
            datetime(2012, 3, 1),
            datetime(2012, 4, 1),
            datetime(2012, 5, 1),
            datetime(2012, 6, 1),
            datetime(2012, 7, 1),
            datetime(2012, 8, 1),
            datetime(2012, 9, 1),
            datetime(2012, 10, 1),
            datetime(2012, 11, 1),
            datetime(2012, 12, 1),
            datetime(2013, 1, 1),
            datetime(2013, 2, 1),
        ]

    def test_single_collection_with_yearly_frequency(self):
        time_vector = [
            datetime(2010, 1, 1),
            datetime(2010, 2, 1),
            datetime(2010, 3, 1),
            datetime(2010, 4, 1),
            datetime(2010, 5, 1),
            datetime(2010, 6, 1),
            datetime(2010, 7, 1),
            datetime(2010, 8, 1),
            datetime(2010, 9, 1),
            datetime(2010, 10, 1),
            datetime(2010, 11, 1),
            datetime(2010, 12, 1),
            datetime(2011, 1, 1),
            datetime(2011, 2, 1),
            datetime(2011, 3, 1),
            datetime(2011, 4, 1),
            datetime(2011, 5, 1),
            datetime(2011, 6, 1),
            datetime(2011, 7, 1),
            datetime(2011, 8, 1),
            datetime(2011, 9, 1),
            datetime(2011, 10, 1),
            datetime(2011, 11, 1),
            datetime(2011, 12, 1),
        ]

        global_time_vector = get_global_time_vector(
            time_series_time_vector=time_vector, frequency=libecalc.common.time_utils.Frequency.YEAR
        )

        # Time vector is not filtered based on frequency, only there to make sure all frequencies are present.
        time_vector.append(datetime(2012, 1, 1))
        assert global_time_vector == time_vector

    def test_trim_start(self):
        # trim with date already present
        global_time_vector = get_global_time_vector(
            time_series_time_vector=[
                datetime(2010, 1, 1),
                datetime(2011, 1, 1),
                datetime(2012, 1, 1),
                datetime(2013, 1, 1),
            ],
            start=datetime(2011, 1, 1),
        )
        assert global_time_vector == [datetime(2011, 1, 1), datetime(2012, 1, 1), datetime(2013, 1, 1)]

        # trim with date not present
        global_time_vector = get_global_time_vector(
            time_series_time_vector=[
                datetime(2010, 1, 1),
                datetime(2011, 1, 1),
                datetime(2012, 1, 1),
                datetime(2013, 1, 1),
            ],
            start=datetime(2011, 1, 2),
        )
        assert global_time_vector == [datetime(2011, 1, 2), datetime(2012, 1, 1), datetime(2013, 1, 1)]

    def test_trim_end(self):
        # trim with date already present
        global_time_vector = get_global_time_vector(
            time_series_time_vector=[
                datetime(2010, 1, 1),
                datetime(2011, 1, 1),
                datetime(2012, 1, 1),
                datetime(2013, 1, 1),
            ],
            end=datetime(2011, 1, 1),
        )
        assert global_time_vector == [datetime(2010, 1, 1), datetime(2011, 1, 1)]

        # trim with date not present
        global_time_vector = get_global_time_vector(
            time_series_time_vector=[
                datetime(2010, 1, 1),
                datetime(2011, 1, 1),
                datetime(2012, 1, 1),
                datetime(2013, 1, 1),
            ],
            end=datetime(2011, 2, 2),
        )
        assert global_time_vector == [datetime(2010, 1, 1), datetime(2011, 1, 1), datetime(2011, 2, 2)]

    def test_additional_dates(self):
        global_time_vector = get_global_time_vector(
            time_series_time_vector=[
                datetime(2010, 1, 1),
                datetime(2011, 1, 1),
                datetime(2012, 1, 1),
                datetime(2013, 1, 1),
            ],
            additional_dates={datetime(2011, 6, 1), datetime(2013, 2, 1)},
        )

        # Include additional_dates within start,end, but should not 'expand' the time_vector start,end by
        # adding dates outside
        assert global_time_vector == [
            datetime(2010, 1, 1),
            datetime(2011, 1, 1),
            datetime(2011, 6, 1),
            datetime(2012, 1, 1),
            datetime(2013, 1, 1),
        ]

    def test_only_start_and_frequency(self):
        assert get_global_time_vector(
            time_series_time_vector=[], start=datetime(2020, 1, 1), frequency=Frequency.YEAR
        ) == [datetime(2020, 1, 1), datetime(2021, 1, 1)]
        assert get_global_time_vector(
            time_series_time_vector=[], start=datetime(2020, 1, 1), frequency=Frequency.MONTH
        ) == [datetime(2020, 1, 1), datetime(2020, 2, 1)]
        assert get_global_time_vector(
            time_series_time_vector=[], start=datetime(2020, 1, 1), frequency=Frequency.DAY
        ) == [datetime(2020, 1, 1), datetime(2020, 1, 2)]

    def test_only_start_and_end(self):
        assert get_global_time_vector(
            time_series_time_vector=[], start=datetime(2020, 1, 1), end=datetime(2021, 1, 1)
        ) == [datetime(2020, 1, 1), datetime(2021, 1, 1)]
        assert get_global_time_vector(
            time_series_time_vector=[], start=datetime(2020, 1, 1), end=datetime(2020, 2, 1)
        ) == [datetime(2020, 1, 1), datetime(2020, 2, 1)]
        assert get_global_time_vector(
            time_series_time_vector=[], start=datetime(2020, 1, 1), end=datetime(2020, 1, 2)
        ) == [datetime(2020, 1, 1), datetime(2020, 1, 2)]

    def test_only_start(self):
        with pytest.raises(ValidationError) as exc_info:
            get_global_time_vector(time_series_time_vector=[], start=datetime(2020, 1, 1))
        assert "No time series found" in str(exc_info.value)

    def test_only_end(self):
        with pytest.raises(ValidationError) as exc_info:
            get_global_time_vector(time_series_time_vector=[], end=datetime(2020, 1, 1))
        assert "No time series found" in str(exc_info.value)

    def test_only_freq(self):
        with pytest.raises(ValidationError) as exc_info:
            get_global_time_vector(time_series_time_vector=[], frequency=Frequency.YEAR)
        assert "No time series found" in str(exc_info.value)

    def test_only_freq_and_end(self):
        with pytest.raises(ValidationError) as exc_info:
            get_global_time_vector(time_series_time_vector=[], frequency=Frequency.YEAR, end=datetime(2020, 1, 1))
        assert "No time series found" in str(exc_info.value)

    def test_only_empty_time_series(self):
        with pytest.raises(ValidationError) as exc_info:
            get_global_time_vector(time_series_time_vector=[])
        assert "No time series found" in str(exc_info.value)


def create_time_series(interpolation_type: InterpolationType, extrapolate: bool):
    return TimeSeries(
        reference_id="COL1_RATE",
        time_vector=[datetime(2010, 1, 1), datetime(2011, 1, 1), datetime(2012, 1, 1), datetime(2013, 1, 1)],
        series=[1, 2, 3, 4],
        interpolation_type=interpolation_type,
        extrapolate=extrapolate,
    )


class TestFitTimeSeriesToTimeVector:
    def test_interpolate_linear(self):
        time_vector = [
            datetime(2010, 1, 1),
            datetime(2011, 1, 1),
            datetime(2011, 6, 1),
            datetime(2012, 1, 1),
            datetime(2013, 1, 1),
        ]

        rate_time_series = TimeSeries(
            reference_id="COL1_RATE",
            time_vector=[datetime(2010, 1, 1), datetime(2011, 1, 1), datetime(2012, 1, 1), datetime(2013, 1, 1)],
            series=[1, 2, 3, 4],
            interpolation_type=InterpolationType.LINEAR,
            extrapolate=False,
        )
        fitted_rate_time_series = rate_time_series.fit_to_time_vector(time_vector)

        # Interpolate based on interpolation type
        assert fitted_rate_time_series.series == [1, 2, 2.4136986301369863, 3, 4]

    def test_interpolate_left(self):
        time_vector = [
            datetime(2010, 1, 1),
            datetime(2011, 1, 1),
            datetime(2011, 6, 1),
            datetime(2012, 1, 1),
            datetime(2013, 1, 1),
        ]

        rate_time_series = TimeSeries(
            reference_id="COL1_RATE",
            time_vector=[datetime(2010, 1, 1), datetime(2011, 1, 1), datetime(2012, 1, 1), datetime(2013, 1, 1)],
            series=[1, 2, 3, 4],
            interpolation_type=InterpolationType.LEFT,
            extrapolate=False,
        )

        fitted_rate_time_series = rate_time_series.fit_to_time_vector(time_vector)

        # Interpolate based on interpolation type
        assert fitted_rate_time_series.series == [1, 2, 3, 3, 4]
        assert fitted_rate_time_series.time_vector == time_vector

    def test_interpolate_right(self):
        time_vector = [
            datetime(2010, 1, 1),
            datetime(2011, 1, 1),
            datetime(2011, 6, 1),
            datetime(2012, 1, 1),
            datetime(2013, 1, 1),
        ]

        rate_time_series = TimeSeries(
            reference_id="COL1_RATE",
            time_vector=[datetime(2010, 1, 1), datetime(2011, 1, 1), datetime(2012, 1, 1), datetime(2013, 1, 1)],
            series=[1, 2, 3, 4],
            interpolation_type=InterpolationType.RIGHT,
            extrapolate=False,
        )
        fitted_rate_time_series = rate_time_series.fit_to_time_vector(time_vector)

        # Interpolate based on interpolation type
        assert fitted_rate_time_series.series == [1, 2, 2, 3, 4]
        assert fitted_rate_time_series.time_vector == time_vector

    def test_extrapolate_outside_true(self):
        time_vector = [
            datetime(2009, 1, 1),
            datetime(2010, 1, 1),
            datetime(2011, 1, 1),
            datetime(2012, 1, 1),
            datetime(2013, 1, 1),
            datetime(2014, 1, 1),
        ]

        rate_time_series = TimeSeries(
            reference_id="COL1_RATE",
            time_vector=[datetime(2010, 1, 1), datetime(2011, 1, 1), datetime(2012, 1, 1), datetime(2013, 1, 1)],
            series=[1, 2, 3, 4],
            interpolation_type=InterpolationType.LINEAR,
            extrapolate=True,
        )
        fitted_rate_time_series = rate_time_series.fit_to_time_vector(time_vector)

        assert fitted_rate_time_series.series == [0, 1, 2, 3, 4, 4]
        assert fitted_rate_time_series.time_vector == time_vector

    def test_extrapolate_outside_false(self):
        time_vector = [
            datetime(2009, 1, 1),
            datetime(2010, 1, 1),
            datetime(2011, 1, 1),
            datetime(2012, 1, 1),
            datetime(2013, 1, 1),
            datetime(2014, 1, 1),
        ]

        rate_time_series = TimeSeries(
            reference_id="COL1_RATE",
            time_vector=[datetime(2010, 1, 1), datetime(2011, 1, 1), datetime(2012, 1, 1), datetime(2013, 1, 1)],
            series=[1, 2, 3, 4],
            interpolation_type=InterpolationType.LINEAR,
            extrapolate=False,
        )
        fitted_rate_time_series = rate_time_series.fit_to_time_vector(time_vector)
        assert fitted_rate_time_series.series == [0, 1.0, 2.0, 3.0, 4.0, 0.0]
        assert fitted_rate_time_series.time_vector == time_vector

    def test_interpolate_to_shorter_global_time_vector(self):
        all_times = [
            datetime(2009, 1, 1),
            datetime(2011, 1, 1),
            datetime(2012, 7, 1),
            datetime(2014, 1, 1),
        ]

        for i in range(1, 5):
            current_time_vector = all_times[0:i]
            fitted_rate_time_series = create_time_series(
                interpolation_type=InterpolationType.RIGHT,
                extrapolate=True,
            ).fit_to_time_vector(current_time_vector)
            assert fitted_rate_time_series.series == [0, 2, 3, 4][0:i]
            assert fitted_rate_time_series.time_vector == current_time_vector

            fitted_rate_time_series_shifted_left = create_time_series(
                interpolation_type=InterpolationType.LEFT,
                extrapolate=True,
            ).fit_to_time_vector(current_time_vector)
            assert fitted_rate_time_series_shifted_left.series == [0, 2, 4, 4][0:i]
            assert fitted_rate_time_series_shifted_left.time_vector == current_time_vector

            fitted_rate_time_series_shifted_linear = create_time_series(
                interpolation_type=InterpolationType.LINEAR,
                extrapolate=True,
            ).fit_to_time_vector(current_time_vector)
            assert fitted_rate_time_series_shifted_linear.series == [0, 2, 3.4972677595628414, 4][0:i]
            assert fitted_rate_time_series_shifted_linear.time_vector == current_time_vector

        for rate_interp_type in [InterpolationType.LEFT, InterpolationType.RIGHT, InterpolationType.LINEAR]:
            current_time_vector = [all_times[-1]]
            fitted_rate_time_series_outside_interval_no_extrapolation = create_time_series(
                extrapolate=False,
                interpolation_type=rate_interp_type,
            ).fit_to_time_vector(current_time_vector)
            assert fitted_rate_time_series_outside_interval_no_extrapolation.series == [0]
            assert fitted_rate_time_series_outside_interval_no_extrapolation.time_vector == current_time_vector

    def test_interpolate_single_date_to_single_date_global_time_vector(self):
        all_times = [
            datetime(2011, 7, 1),
            datetime(2012, 1, 1),
            datetime(2012, 1, 2),
        ]

        expected_without_extrapolation = [0, 3, 0]
        expected_with_extrapolation = [0, 3, 3]

        fitted_rate_time_series_right_with_extrapolation = []
        fitted_rate_time_series_left_with_extrapolation = []
        fitted_rate_time_series_linear_with_extrapolation = []
        for i in range(3):
            current_time_vector = [all_times[i]]
            fitted_rate_time_series_right_with_extrapolation.append(
                create_single_date_time_series(interpolation_type=InterpolationType.RIGHT, extrapolate=True)
                .fit_to_time_vector(current_time_vector)
                .series[0]
            )
            fitted_rate_time_series_left_with_extrapolation.append(
                create_single_date_time_series(interpolation_type=InterpolationType.LEFT, extrapolate=True)
                .fit_to_time_vector(current_time_vector)
                .series[0]
            )
            fitted_rate_time_series_linear_with_extrapolation.append(
                create_single_date_time_series(interpolation_type=InterpolationType.LINEAR, extrapolate=True)
                .fit_to_time_vector(current_time_vector)
                .series[0]
            )

        assert fitted_rate_time_series_right_with_extrapolation == expected_with_extrapolation
        assert fitted_rate_time_series_left_with_extrapolation == expected_with_extrapolation
        assert fitted_rate_time_series_linear_with_extrapolation == expected_with_extrapolation

        fitted_rate_time_series_right_without_extrapolation = []
        fitted_rate_time_series_left_without_extrapolation = []
        fitted_rate_time_series_linear_without_extrapolation = []
        for i in range(3):
            current_time_vector = [all_times[i]]
            fitted_rate_time_series_right_without_extrapolation.append(
                create_single_date_time_series(interpolation_type=InterpolationType.RIGHT, extrapolate=False)
                .fit_to_time_vector(current_time_vector)
                .series[0]
            )
            fitted_rate_time_series_left_without_extrapolation.append(
                create_single_date_time_series(interpolation_type=InterpolationType.LEFT, extrapolate=False)
                .fit_to_time_vector(current_time_vector)
                .series[0]
            )
            fitted_rate_time_series_linear_without_extrapolation.append(
                create_single_date_time_series(interpolation_type=InterpolationType.LINEAR, extrapolate=False)
                .fit_to_time_vector(current_time_vector)
                .series[0]
            )

        assert fitted_rate_time_series_right_without_extrapolation == expected_without_extrapolation
        assert fitted_rate_time_series_left_without_extrapolation == expected_without_extrapolation
        assert fitted_rate_time_series_linear_without_extrapolation == expected_without_extrapolation


class TestGetEndBoundary:
    @pytest.mark.parametrize(
        "what, end_date, dates",
        [
            (
                "last date is first in set",
                datetime(2025, 1, 1),
                {datetime(2024, 1, 4), datetime(2020, 1, 1), datetime(2021, 1, 1), datetime(2023, 3, 1)},
            ),
            (
                "last date is last in set",
                datetime(2027, 1, 1),
                {datetime(2024, 7, 4), datetime(2020, 1, 1), datetime(2021, 1, 1), datetime(2026, 3, 1)},
            ),
            (
                "last date is middle of set",
                datetime(2022, 1, 1),
                {datetime(2014, 7, 4), datetime(2020, 1, 1), datetime(2021, 1, 1), datetime(2013, 3, 1)},
            ),
            (
                "last date has month and day different from 1 (does not start at beginning of year)",
                datetime(2022, 1, 1),
                {datetime(2014, 7, 4), datetime(2020, 1, 1), datetime(2021, 4, 7), datetime(2013, 3, 1)},
            ),
        ],
    )
    def test_get_end_boundary_yearly_frequency(self, what, end_date, dates):
        print(f"testing {what}")
        assert end_date == _get_end_boundary(Frequency.YEAR, dates)

    @pytest.mark.parametrize(
        "what, end_date, dates",
        [
            (
                "last date is first in set",
                datetime(2024, 2, 1),
                {datetime(2024, 1, 4), datetime(2020, 1, 1), datetime(2021, 1, 1), datetime(2023, 3, 1)},
            ),
            (
                "last date is last in set",
                datetime(2026, 4, 1),
                {datetime(2024, 7, 4), datetime(2020, 1, 1), datetime(2021, 1, 1), datetime(2026, 3, 1)},
            ),
            (
                "last date is middle of set",
                datetime(2021, 2, 1),
                {datetime(2014, 7, 4), datetime(2020, 1, 1), datetime(2021, 1, 1), datetime(2013, 3, 1)},
            ),
            (
                "last date has month and day different from 1 (does not start at beginning of year)",
                datetime(2021, 5, 1),
                {datetime(2014, 7, 4), datetime(2020, 1, 1), datetime(2021, 4, 7), datetime(2013, 3, 1)},
            ),
            (
                "last date is in last month (december)",
                datetime(2022, 1, 1),
                {datetime(2014, 7, 4), datetime(2020, 1, 1), datetime(2021, 12, 7), datetime(2013, 3, 1)},
            ),
        ],
    )
    def test_get_end_boundary_monthly_frequency(self, what, end_date, dates):
        print(f"testing {what}")
        assert end_date == _get_end_boundary(Frequency.MONTH, dates)

    @pytest.mark.parametrize(
        "what, end_date, dates",
        [
            (
                "last date is first in set",
                datetime(2024, 1, 5),
                {datetime(2024, 1, 4), datetime(2020, 1, 1), datetime(2021, 1, 1), datetime(2023, 3, 1)},
            ),
            (
                "last date is last in set",
                datetime(2026, 3, 2),
                {datetime(2024, 7, 4), datetime(2020, 1, 1), datetime(2021, 1, 1), datetime(2026, 3, 1)},
            ),
            (
                "last date is middle of set",
                datetime(2021, 1, 2),
                {datetime(2014, 7, 4), datetime(2020, 1, 1), datetime(2021, 1, 1), datetime(2013, 3, 1)},
            ),
            (
                "last date has month and day different from 1 (does not start at beginning of year)",
                datetime(2021, 4, 8),
                {datetime(2014, 7, 4), datetime(2020, 1, 1), datetime(2021, 4, 7), datetime(2013, 3, 1)},
            ),
            (
                "last date is last day in month",
                datetime(2021, 6, 1),
                {datetime(2014, 7, 4), datetime(2020, 1, 1), datetime(2021, 5, 31), datetime(2013, 3, 1)},
            ),
        ],
    )
    def test_get_end_boundary_daily_frequency(self, what, end_date, dates):
        print(f"testing {what}")
        assert end_date == _get_end_boundary(Frequency.DAY, dates)

    @pytest.mark.parametrize(
        "what, end_date, dates",
        [
            (
                "last date is first in set",
                datetime(2024, 1, 4),
                {datetime(2024, 1, 4), datetime(2020, 1, 1), datetime(2021, 1, 1), datetime(2023, 3, 1)},
            ),
            (
                "last date is last in set",
                datetime(2026, 3, 1),
                {datetime(2024, 7, 4), datetime(2020, 1, 1), datetime(2021, 1, 1), datetime(2026, 3, 1)},
            ),
            (
                "last date is middle of set",
                datetime(2021, 1, 1),
                {datetime(2014, 7, 4), datetime(2020, 1, 1), datetime(2021, 1, 1), datetime(2013, 3, 1)},
            ),
            (
                "last date has month and day different from 1 (does not start at beginning of year)",
                datetime(2021, 4, 7),
                {datetime(2014, 7, 4), datetime(2020, 1, 1), datetime(2021, 4, 7), datetime(2013, 3, 1)},
            ),
        ],
    )
    def test_get_end_boundary_no_frequency_given(self, what, end_date, dates):
        print(f"testing {what}")
        assert end_date == _get_end_boundary(Frequency.NONE, dates)
