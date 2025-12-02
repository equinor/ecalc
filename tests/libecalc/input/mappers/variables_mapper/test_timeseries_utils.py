from datetime import datetime

import pytest

import libecalc.common.time_utils
from libecalc.common.time_utils import Frequency
from libecalc.domain.component_validation_error import DomainValidationException
from libecalc.dto.types import InterpolationType
from libecalc.presentation.yaml.domain.time_series import TimeSeries
from libecalc.presentation.yaml.mappers.variables_mapper.get_global_time_vector import get_global_time_vector
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
    def test_trim_start_and_end(self):
        test_cases = [
            (
                datetime(2010, 1, 1),
                datetime(2013, 1, 1),
                [datetime(2010, 1, 1), datetime(2011, 1, 1), datetime(2012, 1, 1), datetime(2013, 1, 1)],
            ),
            (
                datetime(2010, 6, 1),
                datetime(2013, 1, 1),
                [datetime(2010, 6, 1), datetime(2011, 1, 1), datetime(2012, 1, 1), datetime(2013, 1, 1)],
            ),
            (datetime(2011, 1, 1), datetime(2012, 1, 1), [datetime(2011, 1, 1), datetime(2012, 1, 1)]),
            (
                datetime(2011, 6, 1),
                datetime(2012, 6, 1),
                [datetime(2011, 6, 1), datetime(2012, 1, 1), datetime(2012, 6, 1)],
            ),
        ]

        time_series_time_vector = [
            datetime(2010, 1, 1),
            datetime(2011, 1, 1),
            datetime(2012, 1, 1),
            datetime(2013, 1, 1),
        ]

        for start, end, expected in test_cases:
            global_time_vector = get_global_time_vector(
                time_series_time_vector=time_series_time_vector,
                start=start,
                end=end,
            )
            assert global_time_vector == expected

    def test_additional_dates(self):
        global_time_vector = get_global_time_vector(
            time_series_time_vector=[
                datetime(2010, 1, 1),
                datetime(2011, 1, 1),
                datetime(2012, 1, 1),
                datetime(2013, 1, 1),
            ],
            end=datetime(2013, 1, 1),
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

    def test_only_end(self):
        with pytest.raises(DomainValidationException) as exc_info:
            get_global_time_vector(time_series_time_vector=[], end=datetime(2020, 1, 1))
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
