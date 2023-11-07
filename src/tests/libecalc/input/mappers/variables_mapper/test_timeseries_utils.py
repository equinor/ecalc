from datetime import datetime

import libecalc.common.time_utils
import pytest
from libecalc.common.time_utils import Frequency
from libecalc.dto.types import InterpolationType
from libecalc.presentation.yaml.mappers.variables_mapper.time_series_collection import (
    MiscellaneousTimeSeriesCollection,
)
from libecalc.presentation.yaml.mappers.variables_mapper.timeseries_utils import (
    _get_end_boundary,
    fit_time_series_to_time_vector,
    get_global_time_vector,
)


@pytest.fixture
def miscellaneous_time_series_collection_yearly():
    return MiscellaneousTimeSeriesCollection(
        name="test",
        headers=["COL1_RATE", "COL2"],
        columns=[[1, 2, 3, 4], [2, 4, 6, 8]],
        time_vector=[datetime(2010, 1, 1), datetime(2011, 1, 1), datetime(2012, 1, 1), datetime(2013, 1, 1)],
        interpolation_type=InterpolationType.RIGHT,
    )


@pytest.fixture
def miscellaneous_time_series_collection_single_date():
    return MiscellaneousTimeSeriesCollection(
        name="test",
        headers=["COL1_RATE", "COL2"],
        columns=[[3], [6]],
        time_vector=[datetime(2012, 1, 1)],
        interpolation_type=InterpolationType.RIGHT,
    )


class TestGetGlobalTimeVector:
    def test_single_collection(self, miscellaneous_time_series_collection_yearly):
        global_time_vector = get_global_time_vector(
            time_series_collections=[miscellaneous_time_series_collection_yearly],
        )

        assert global_time_vector == [
            datetime(2010, 1, 1),
            datetime(2011, 1, 1),
            datetime(2012, 1, 1),
            datetime(2013, 1, 1),
        ]

    def test_single_collection_with_monthly_frequency(self, miscellaneous_time_series_collection_yearly):
        global_time_vector = get_global_time_vector(
            time_series_collections=[miscellaneous_time_series_collection_yearly],
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
        time_series_collection = MiscellaneousTimeSeriesCollection(
            name="test",
            headers=["COL1", "COL2"],
            columns=[[1.0] * len(time_vector), [2.0] * len(time_vector)],
            time_vector=time_vector,
            interpolation_type=InterpolationType.RIGHT,
        )

        global_time_vector = get_global_time_vector(
            time_series_collections=[time_series_collection], frequency=libecalc.common.time_utils.Frequency.YEAR
        )

        # Time vector is not filtered based on frequency, only there to make sure all frequencies are present.
        time_vector.append(datetime(2012, 1, 1))
        assert global_time_vector == time_vector

    def test_trim_start(self, miscellaneous_time_series_collection_yearly):
        # trim with date already present
        global_time_vector = get_global_time_vector(
            time_series_collections=[miscellaneous_time_series_collection_yearly], start=datetime(2011, 1, 1)
        )
        assert global_time_vector == [datetime(2011, 1, 1), datetime(2012, 1, 1), datetime(2013, 1, 1)]

        # trim with date not present
        global_time_vector = get_global_time_vector(
            time_series_collections=[miscellaneous_time_series_collection_yearly], start=datetime(2011, 1, 2)
        )
        assert global_time_vector == [datetime(2011, 1, 2), datetime(2012, 1, 1), datetime(2013, 1, 1)]

    def test_trim_end(self, miscellaneous_time_series_collection_yearly):
        # trim with date already present
        global_time_vector = get_global_time_vector(
            time_series_collections=[miscellaneous_time_series_collection_yearly], end=datetime(2011, 1, 1)
        )
        assert global_time_vector == [datetime(2010, 1, 1), datetime(2011, 1, 1)]

        # trim with date not present
        global_time_vector = get_global_time_vector(
            time_series_collections=[miscellaneous_time_series_collection_yearly], end=datetime(2011, 2, 2)
        )
        assert global_time_vector == [datetime(2010, 1, 1), datetime(2011, 1, 1), datetime(2011, 2, 2)]

    def test_additional_dates(self, miscellaneous_time_series_collection_yearly):
        global_time_vector = get_global_time_vector(
            time_series_collections=[miscellaneous_time_series_collection_yearly],
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
            time_series_collections=[], start=datetime(2020, 1, 1), frequency=Frequency.YEAR
        ) == [datetime(2020, 1, 1), datetime(2021, 1, 1)]
        assert get_global_time_vector(
            time_series_collections=[], start=datetime(2020, 1, 1), frequency=Frequency.MONTH
        ) == [datetime(2020, 1, 1), datetime(2020, 2, 1)]
        assert get_global_time_vector(
            time_series_collections=[], start=datetime(2020, 1, 1), frequency=Frequency.DAY
        ) == [datetime(2020, 1, 1), datetime(2020, 1, 2)]

    def test_only_start_and_end(self):
        assert get_global_time_vector(
            time_series_collections=[], start=datetime(2020, 1, 1), end=datetime(2021, 1, 1)
        ) == [datetime(2020, 1, 1), datetime(2021, 1, 1)]
        assert get_global_time_vector(
            time_series_collections=[], start=datetime(2020, 1, 1), end=datetime(2020, 2, 1)
        ) == [datetime(2020, 1, 1), datetime(2020, 2, 1)]
        assert get_global_time_vector(
            time_series_collections=[], start=datetime(2020, 1, 1), end=datetime(2020, 1, 2)
        ) == [datetime(2020, 1, 1), datetime(2020, 1, 2)]

    def test_only_start(self):
        with pytest.raises(ValueError) as exc_info:
            get_global_time_vector(time_series_collections=[], start=datetime(2020, 1, 1))
        assert "No time series found" in str(exc_info.value)

    def test_only_end(self):
        with pytest.raises(ValueError) as exc_info:
            get_global_time_vector(time_series_collections=[], end=datetime(2020, 1, 1))
        assert "No time series found" in str(exc_info.value)

    def test_only_freq(self):
        with pytest.raises(ValueError) as exc_info:
            get_global_time_vector(time_series_collections=[], frequency=Frequency.YEAR)
        assert "No time series found" in str(exc_info.value)

    def test_only_freq_and_end(self):
        with pytest.raises(ValueError) as exc_info:
            get_global_time_vector(time_series_collections=[], frequency=Frequency.YEAR, end=datetime(2020, 1, 1))
        assert "No time series found" in str(exc_info.value)

    def test_only_empty_time_series(self):
        with pytest.raises(ValueError) as exc_info:
            get_global_time_vector(time_series_collections=[])
        assert "No time series found" in str(exc_info.value)


class TestFitTimeSeriesToTimeVector:
    def test_interpolate_linear(self, miscellaneous_time_series_collection_yearly):
        time_series = miscellaneous_time_series_collection_yearly.time_series

        time_vector = [
            datetime(2010, 1, 1),
            datetime(2011, 1, 1),
            datetime(2011, 6, 1),
            datetime(2012, 1, 1),
            datetime(2013, 1, 1),
        ]

        rate_time_series = time_series[0]
        fitted_rate_time_series = fit_time_series_to_time_vector(
            time_series=rate_time_series,
            time_vector=time_vector,
            interpolation_type=InterpolationType.LINEAR,
            extrapolate_outside_defined_time_interval=False,
        )

        # Interpolate based on interpolation type
        assert fitted_rate_time_series == [1, 2, 2.4136986301369863, 3, 4]

        non_rate_time_series = time_series[1]
        fitted_time_series = fit_time_series_to_time_vector(
            time_series=non_rate_time_series,
            time_vector=time_vector,
            interpolation_type=InterpolationType.RIGHT,
            extrapolate_outside_defined_time_interval=False,
        )

        # Interpolate based on interpolation type
        assert fitted_time_series == [2.0, 4.0, 4.0, 6.0, 8.0]

    def test_interpolate_left(self, miscellaneous_time_series_collection_yearly):
        time_series = miscellaneous_time_series_collection_yearly.time_series

        time_vector = [
            datetime(2010, 1, 1),
            datetime(2011, 1, 1),
            datetime(2011, 6, 1),
            datetime(2012, 1, 1),
            datetime(2013, 1, 1),
        ]

        rate_time_series = time_series[0]

        fitted_rate_time_series = fit_time_series_to_time_vector(
            time_series=rate_time_series,
            time_vector=time_vector,
            interpolation_type=InterpolationType.LEFT,
            extrapolate_outside_defined_time_interval=False,
        )

        # Interpolate based on interpolation type
        assert fitted_rate_time_series == [1, 2, 3, 3, 4]

        non_rate_time_series = time_series[1]
        fitted_time_series = fit_time_series_to_time_vector(
            time_series=non_rate_time_series,
            time_vector=time_vector,
            interpolation_type=InterpolationType.LEFT,
            extrapolate_outside_defined_time_interval=False,
        )

        # Interpolate based on interpolation type
        assert fitted_time_series == [2.0, 4.0, 6.0, 6.0, 8.0]

    def test_interpolate_right(self, miscellaneous_time_series_collection_yearly):
        time_series = miscellaneous_time_series_collection_yearly.time_series

        time_vector = [
            datetime(2010, 1, 1),
            datetime(2011, 1, 1),
            datetime(2011, 6, 1),
            datetime(2012, 1, 1),
            datetime(2013, 1, 1),
        ]

        rate_time_series = time_series[0]
        fitted_rate_time_series = fit_time_series_to_time_vector(
            time_series=rate_time_series,
            time_vector=time_vector,
            interpolation_type=InterpolationType.RIGHT,
            extrapolate_outside_defined_time_interval=False,
        )

        # Interpolate based on interpolation type
        assert fitted_rate_time_series == [1, 2, 2, 3, 4]

        non_rate_time_series = time_series[1]
        fitted_time_series = fit_time_series_to_time_vector(
            time_series=non_rate_time_series,
            time_vector=time_vector,
            interpolation_type=InterpolationType.RIGHT,
            extrapolate_outside_defined_time_interval=False,
        )

        # Interpolate based on interpolation type
        assert fitted_time_series == [2.0, 4.0, 4.0, 6.0, 8.0]

    def test_extrapolate_outside_true(self, miscellaneous_time_series_collection_yearly):
        time_series = miscellaneous_time_series_collection_yearly.time_series
        time_vector = [
            datetime(2009, 1, 1),
            datetime(2010, 1, 1),
            datetime(2011, 1, 1),
            datetime(2012, 1, 1),
            datetime(2013, 1, 1),
            datetime(2014, 1, 1),
        ]

        rate_time_series = time_series[0]
        fitted_rate_time_series = fit_time_series_to_time_vector(
            time_series=rate_time_series,
            time_vector=time_vector,
            extrapolate_outside_defined_time_interval=True,
            interpolation_type=InterpolationType.LINEAR,
        )
        # Rate should use extrapolate_outside_defined_time_interval to decide extrapolation
        assert fitted_rate_time_series == [0, 1, 2, 3, 4, 4]

        # Check that Non-rate behaves like rate
        non_rate_time_series = time_series[1]
        fitted_time_series = fit_time_series_to_time_vector(
            time_series=non_rate_time_series,
            time_vector=time_vector,
            interpolation_type=InterpolationType.RIGHT,
            extrapolate_outside_defined_time_interval=True,
        )
        assert fitted_time_series == [0, 2.0, 4.0, 6.0, 8.0, 8.0]

    def test_extrapolate_outside_false(self, miscellaneous_time_series_collection_yearly):
        time_series = miscellaneous_time_series_collection_yearly.time_series
        time_vector = [
            datetime(2009, 1, 1),
            datetime(2010, 1, 1),
            datetime(2011, 1, 1),
            datetime(2012, 1, 1),
            datetime(2013, 1, 1),
            datetime(2014, 1, 1),
        ]

        rate_time_series = time_series[0]
        fitted_rate_time_series = fit_time_series_to_time_vector(
            time_series=rate_time_series,
            time_vector=time_vector,
            extrapolate_outside_defined_time_interval=False,
            interpolation_type=InterpolationType.LINEAR,
        )
        # Rate should use extrapolate_outside_defined_time_interval to decide extrapolation
        assert fitted_rate_time_series == [0, 1.0, 2.0, 3.0, 4.0, 0.0]

        # Check that Non-rate behaves like rate
        non_rate_time_series = time_series[1]
        fitted_time_series = fit_time_series_to_time_vector(
            time_series=non_rate_time_series,
            time_vector=time_vector,
            interpolation_type=InterpolationType.RIGHT,
            extrapolate_outside_defined_time_interval=False,
        )
        assert fitted_time_series == [0.0, 2.0, 4.0, 6.0, 8.0, 0.0]

    def test_interpolate_to_shorter_global_time_vector(self, miscellaneous_time_series_collection_yearly):
        time_series = miscellaneous_time_series_collection_yearly.time_series
        rate_time_series = time_series[0]

        time_vector = [
            datetime(2009, 1, 1),
            datetime(2011, 1, 1),
            datetime(2012, 7, 1),
            datetime(2014, 1, 1),
        ]

        for i in range(1, 5):
            fitted_rate_time_series = fit_time_series_to_time_vector(
                time_series=rate_time_series,
                time_vector=time_vector[0:i],
                extrapolate_outside_defined_time_interval=True,
                interpolation_type=InterpolationType.RIGHT,
            )
            assert fitted_rate_time_series == [0, 2, 3, 4][0:i]
            fitted_rate_time_series_shifted_left = fit_time_series_to_time_vector(
                time_series=rate_time_series,
                time_vector=time_vector[0:i],
                extrapolate_outside_defined_time_interval=True,
                interpolation_type=InterpolationType.LEFT,
            )
            assert fitted_rate_time_series_shifted_left == [0, 2, 4, 4][0:i]
            fitted_rate_time_series_shifted_linear = fit_time_series_to_time_vector(
                time_series=rate_time_series,
                time_vector=time_vector[0:i],
                extrapolate_outside_defined_time_interval=True,
                interpolation_type=InterpolationType.LINEAR,
            )
            assert fitted_rate_time_series_shifted_linear == [0, 2, 3.4972677595628414, 4][0:i]

        for rate_interp_type in [InterpolationType.LEFT, InterpolationType.RIGHT, InterpolationType.LINEAR]:
            fitted_rate_time_series_outside_interval_no_extrapolation = fit_time_series_to_time_vector(
                time_series=rate_time_series,
                time_vector=[time_vector[-1]],
                extrapolate_outside_defined_time_interval=False,
                interpolation_type=rate_interp_type,
            )
            assert fitted_rate_time_series_outside_interval_no_extrapolation == [0]

    def test_interpolate_single_date_to_single_date_global_time_vector(
        self, miscellaneous_time_series_collection_single_date
    ):
        time_series = miscellaneous_time_series_collection_single_date.time_series
        rate_time_series = time_series[0]

        time_vector = [
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
            fitted_rate_time_series_right_with_extrapolation.append(
                fit_time_series_to_time_vector(
                    time_series=rate_time_series,
                    time_vector=[time_vector[i]],
                    extrapolate_outside_defined_time_interval=True,
                    interpolation_type=InterpolationType.RIGHT,
                )[0]
            )
            fitted_rate_time_series_left_with_extrapolation.append(
                fit_time_series_to_time_vector(
                    time_series=rate_time_series,
                    time_vector=[time_vector[i]],
                    extrapolate_outside_defined_time_interval=True,
                    interpolation_type=InterpolationType.LEFT,
                )[0]
            )
            fitted_rate_time_series_linear_with_extrapolation.append(
                fit_time_series_to_time_vector(
                    time_series=rate_time_series,
                    time_vector=[time_vector[i]],
                    extrapolate_outside_defined_time_interval=True,
                    interpolation_type=InterpolationType.LINEAR,
                )[0]
            )

        assert fitted_rate_time_series_right_with_extrapolation == expected_with_extrapolation
        assert fitted_rate_time_series_left_with_extrapolation == expected_with_extrapolation
        assert fitted_rate_time_series_linear_with_extrapolation == expected_with_extrapolation

        fitted_rate_time_series_right_without_extrapolation = []
        fitted_rate_time_series_left_without_extrapolation = []
        fitted_rate_time_series_linear_without_extrapolation = []
        for i in range(3):
            fitted_rate_time_series_right_without_extrapolation.append(
                fit_time_series_to_time_vector(
                    time_series=rate_time_series,
                    time_vector=[time_vector[i]],
                    extrapolate_outside_defined_time_interval=False,
                    interpolation_type=InterpolationType.RIGHT,
                )[0]
            )
            fitted_rate_time_series_left_without_extrapolation.append(
                fit_time_series_to_time_vector(
                    time_series=rate_time_series,
                    time_vector=[time_vector[i]],
                    extrapolate_outside_defined_time_interval=False,
                    interpolation_type=InterpolationType.LEFT,
                )[0]
            )
            fitted_rate_time_series_linear_without_extrapolation.append(
                fit_time_series_to_time_vector(
                    time_series=rate_time_series,
                    time_vector=[time_vector[i]],
                    extrapolate_outside_defined_time_interval=False,
                    interpolation_type=InterpolationType.LINEAR,
                )[0]
            )

        assert fitted_rate_time_series_right_without_extrapolation == expected_without_extrapolation
        assert fitted_rate_time_series_left_without_extrapolation == expected_without_extrapolation
        assert fitted_rate_time_series_linear_without_extrapolation == expected_without_extrapolation

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
