from datetime import datetime

import pytest
from pydantic import BaseModel

from libecalc.common.tabular_time_series import TabularTimeSeriesUtils
from libecalc.common.time_utils import Period, Periods
from libecalc.common.units import Unit
from libecalc.common.utils.rates import (
    TimeSeriesFloat,
    TimeSeriesStreamDayRate,
)


class MergeableObject(BaseModel):
    string_test: str
    int_test: int
    float_test: float
    list_of_float_test: list[float]
    time_series_float: TimeSeriesFloat
    time_series_rate: TimeSeriesStreamDayRate
    time_series_float_list_test: list[TimeSeriesFloat]
    time_series_rate_list_test: list[TimeSeriesStreamDayRate]


class TestMerge:
    def test_valid_merge(self):
        first_periods = Periods.create_periods(
            times=[
                datetime(2020, 1, 1),
                datetime(2021, 1, 1),
                datetime(2022, 1, 1),
            ],
            include_after=False,
            include_before=False,
        )
        first = MergeableObject(
            string_test="1",
            int_test=15,
            float_test=1.0,
            list_of_float_test=[11, 12, 13, 14, 15],
            time_series_rate=TimeSeriesStreamDayRate(
                periods=first_periods,
                values=[11, 12],
                unit=Unit.TONS,
            ),
            time_series_float=TimeSeriesFloat(
                periods=first_periods,
                values=[11, 12],
                unit=Unit.TONS,
            ),
            time_series_float_list_test=[
                TimeSeriesFloat(
                    periods=first_periods,
                    values=[111, 112],
                    unit=Unit.TONS,
                ),
                TimeSeriesFloat(
                    periods=first_periods,
                    values=[-111, -112],
                    unit=Unit.TONS,
                ),
            ],
            time_series_rate_list_test=[
                TimeSeriesStreamDayRate(
                    periods=first_periods,
                    values=[111, 112],
                    unit=Unit.TONS,
                ),
                TimeSeriesStreamDayRate(
                    periods=first_periods,
                    values=[-111, -112],
                    unit=Unit.TONS,
                ),
            ],
        )

        second_periods = Periods.create_periods(
            times=[
                datetime(2022, 1, 1),
                datetime(2023, 1, 1),
                datetime(2024, 1, 1),
            ],
            include_after=False,
            include_before=False,
        )
        second = MergeableObject(
            string_test="2",
            int_test=25,
            float_test=2.0,
            list_of_float_test=[21, 22, 23, 24, 25],
            time_series_float=TimeSeriesFloat(
                periods=second_periods,
                values=[21, 22],
                unit=Unit.TONS,
            ),
            time_series_rate=TimeSeriesStreamDayRate(
                periods=second_periods,
                values=[21, 22],
                unit=Unit.TONS,
            ),
            time_series_float_list_test=[
                TimeSeriesFloat(
                    periods=second_periods,
                    values=[211, 212],
                    unit=Unit.TONS,
                ),
                TimeSeriesFloat(
                    periods=second_periods,
                    values=[-211, -212],
                    unit=Unit.TONS,
                ),
            ],
            time_series_rate_list_test=[
                TimeSeriesStreamDayRate(
                    periods=second_periods,
                    values=[211, 212],
                    unit=Unit.TONS,
                ),
                TimeSeriesStreamDayRate(
                    periods=second_periods,
                    values=[-211, -212],
                    unit=Unit.TONS,
                ),
            ],
        )

        merged = TabularTimeSeriesUtils.merge(first, second)

        expected_periods = Periods.create_periods(
            times=[
                datetime(2020, 1, 1),
                datetime(2021, 1, 1),
                datetime(2022, 1, 1),
                datetime(2023, 1, 1),
                datetime(2024, 1, 1),
            ],
            include_after=False,
            include_before=False,
        )

        assert (
            merged.model_dump()
            == MergeableObject(
                string_test="1",
                int_test=15,
                float_test=1.0,
                list_of_float_test=[11, 12, 13, 14, 15],
                time_series_float=TimeSeriesFloat(
                    periods=expected_periods,
                    values=[11, 12, 21, 22],
                    unit=Unit.TONS,
                ),
                time_series_rate=TimeSeriesStreamDayRate(
                    periods=expected_periods,
                    values=[11, 12, 21, 22],
                    unit=Unit.TONS,
                ),
                time_series_float_list_test=[
                    TimeSeriesFloat(
                        periods=expected_periods,
                        values=[111, 112, 211, 212],
                        unit=Unit.TONS,
                    ),
                    TimeSeriesFloat(
                        periods=expected_periods,
                        values=[-111, -112, -211, -212],
                        unit=Unit.TONS,
                    ),
                ],
                time_series_rate_list_test=[
                    TimeSeriesStreamDayRate(
                        periods=expected_periods,
                        values=[111, 112, 211, 212],
                        unit=Unit.TONS,
                    ),
                    TimeSeriesStreamDayRate(
                        periods=expected_periods,
                        values=[-111, -112, -211, -212],
                        unit=Unit.TONS,
                    ),
                ],
            ).model_dump()
        )

    def test_invalid_types(self):
        class First(BaseModel):
            something: TimeSeriesFloat

        first = First(
            something=TimeSeriesFloat(
                periods=Periods(
                    [Period(datetime(2022, 1, 1))],
                ),
                values=[1],
                unit=Unit.NONE,
            )
        )

        class Other(BaseModel):
            something: list[int]

        other = Other(something=[1, 2])

        with pytest.raises(ValueError) as exc_info:
            TabularTimeSeriesUtils.merge(first, other)

        assert str(exc_info.value) == "Can not merge objects of differing types."
