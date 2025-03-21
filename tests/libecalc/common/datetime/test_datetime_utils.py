from datetime import datetime
from libecalc.common.datetime.utils import DateUtils
from libecalc.common.time_utils import Period, Periods


class TestDateUtils:
    def test_serialize_datetime(self):
        date = datetime(2023, 10, 5, 14, 30, 0)
        expected = "2023-10-05 14:30:00"
        assert DateUtils.serialize(date) == expected

    def test_serialize_str(self):
        date_str = "2023-10-05 14:30:00"
        expected = "2023-10-05 14:30:00"
        assert DateUtils.serialize(date_str) == expected

    def test_serialize_list(self):
        dates = [datetime(2023, 10, 5, 14, 30, 0), datetime(2023, 10, 6, 15, 45, 0)]
        expected = ["2023-10-05 14:30:00", "2023-10-06 15:45:00"]
        assert DateUtils.serialize(dates) == expected

    def test_serialize_dict(self):
        dates = {"start": datetime(2023, 10, 5, 14, 30, 0), "end": datetime(2023, 10, 6, 15, 45, 0)}
        expected = {"start": "2023-10-05 14:30:00", "end": "2023-10-06 15:45:00"}
        assert DateUtils.serialize(dates) == expected

    def test_serialize_invalid_str(self, caplog):
        invalid_date_str = "invalid date"
        with caplog.at_level("WARNING"):
            result = DateUtils.serialize(invalid_date_str)
            assert result == invalid_date_str
            assert any("Failed to parse date string" in message for message in caplog.messages)

    def test_serialize_period(self):
        period = Period(start=datetime(2023, 10, 5, 14, 30, 0), end=datetime(2023, 10, 6, 15, 45, 0))
        expected = {"start": "2023-10-05 14:30:00", "end": "2023-10-06 15:45:00"}
        assert DateUtils.serialize(period) == expected

    def test_serialize_periods(self):
        periods = Periods(
            periods=[
                Period(start=datetime(2023, 10, 5, 14, 30, 0), end=datetime(2023, 10, 6, 15, 45, 0)),
                Period(start=datetime(2023, 10, 7, 16, 0, 0), end=datetime(2023, 10, 8, 17, 30, 0)),
            ]
        )
        expected = {
            "periods": [
                {"start": "2023-10-05 14:30:00", "end": "2023-10-06 15:45:00"},
                {"start": "2023-10-07 16:00:00", "end": "2023-10-08 17:30:00"},
            ]
        }
        assert DateUtils.serialize(periods) == expected
