from datetime import datetime

import pytest
from libecalc.common.time_utils import (
    Period,
    Periods,
    calculate_delta_days,
    define_time_model_for_period,
)


class TestCalculateDeltaDays:
    def test_calculate_delta_dates(self):
        assert calculate_delta_days([datetime(2000, 1, 1), datetime(2001, 1, 1), datetime(2002, 1, 1)]).tolist() == [
            366,
            365,
        ]

    def test_calculate_delta_days_single_date(self):
        assert calculate_delta_days([datetime(2000, 1, 1)]).tolist() == []


class TestPeriod:
    def test_period_repr(self):
        period = Period(start=datetime(2022, 1, 1), end=datetime(2030, 4, 5))
        assert str(period) == "2022-01-01 00:00:00:2030-04-05 00:00:00"
        assert repr(period) == (
            "Period(start=datetime.datetime(2022, 1, 1, 0, 0), " "end=datetime.datetime(2030, 4, 5, 0, 0))"
        )

    def test_start_end_defined(self):
        period = Period(start=datetime(2022, 1, 1), end=datetime(2030, 1, 1))
        assert datetime(2022, 1, 1) in period
        assert datetime(2025, 12, 15) in period
        assert datetime(2030, 1, 1) not in period
        assert datetime(2050, 1, 1) not in period
        assert datetime(2020, 1, 1) not in period

    def test_start_not_defined(self):
        period = Period(end=datetime(2030, 1, 1))
        assert datetime(2022, 1, 1) in period
        assert datetime(2025, 12, 15) in period
        assert datetime(1900, 12, 15) in period
        assert datetime(2030, 1, 1) not in period
        assert datetime(2050, 1, 1) not in period

    def test_end_not_defined(self):
        period = Period(start=datetime(2022, 1, 1))
        assert datetime(2022, 1, 1) in period
        assert datetime(2025, 12, 15) in period
        assert datetime(1900, 12, 15) not in period
        assert datetime(2030, 1, 1) in period
        assert datetime(2050, 1, 1) in period
        assert datetime(4000, 1, 1) in period


class TestCreatePeriods:
    def test_single_date(self):
        single_date = datetime(2020, 1, 1)
        periods = Periods.create_periods([single_date])
        assert periods == Periods(
            [Period(start=datetime.min, end=single_date), Period(start=single_date, end=datetime.max)]
        )

    def test_two_dates(self):
        first_date = datetime(2020, 1, 1)
        second_date = datetime(2022, 1, 1)
        periods = Periods.create_periods([first_date, second_date])
        assert periods == Periods(
            [
                Period(start=datetime.min, end=first_date),
                Period(start=first_date, end=second_date),
                Period(start=second_date, end=datetime.max),
            ]
        )

    def test_three_dates(self):
        first_date = datetime(2020, 1, 1)
        second_date = datetime(2022, 1, 1)
        third_date = datetime(2022, 1, 1)
        periods = Periods.create_periods([first_date, second_date, third_date])
        assert periods == Periods(
            [
                Period(start=datetime.min, end=first_date),
                Period(start=first_date, end=second_date),
                Period(start=second_date, end=third_date),
                Period(start=third_date, end=datetime.max),
            ]
        )


@pytest.fixture
def time_model():
    return {
        datetime(1962, 1, 1): {},
        datetime(1962, 6, 1): {},
        datetime(1970, 1, 1): {},
        datetime(1999, 1, 1): {},
    }


class TestDefineTimeModelForPeriod:
    def test_include_all(self, time_model):
        period = Period(
            start=datetime(1960, 1, 1),
            end=datetime(1999, 1, 2),
        )
        assert define_time_model_for_period(time_model, target_period=period) == {
            datetime(1962, 1, 1): {},
            datetime(1962, 6, 1): {},
            datetime(1970, 1, 1): {},
            datetime(1999, 1, 1): {},
        }

    def test_equal_end(self, time_model):
        period = Period(
            start=datetime(1962, 1, 1),
            end=datetime(1999, 1, 1),
        )
        assert define_time_model_for_period(time_model, target_period=period) == {
            datetime(1962, 1, 1): {},
            datetime(1962, 6, 1): {},
            datetime(1970, 1, 1): {},
        }

    def test_middle(self, time_model):
        period = Period(
            start=datetime(1962, 6, 7),
            end=datetime(1999, 1, 1),
        )
        assert define_time_model_for_period(time_model, target_period=period) == {
            datetime(1962, 6, 7): {},
            datetime(1970, 1, 1): {},
        }

    def test_outside(self, time_model):
        period = Period(
            start=datetime(1950, 1, 1),
            end=datetime(1952, 1, 1),
        )
        assert define_time_model_for_period(time_model, target_period=period) == {}
