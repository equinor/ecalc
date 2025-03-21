import logging
from datetime import datetime
from enum import Enum
from libecalc.common.serializer import Serializer
from libecalc.common.time_utils import Period, Periods

# Configure the logger for testing
logging.basicConfig(level=logging.WARNING)


class SampleEnum(Enum):
    VALUE1 = "value1"
    VALUE2 = "value2"


class SampleClass:
    """
    A sample class to demonstrate serialization.

    Attributes:
        name (str): The name of the sample.
        value (Any): The value associated with the sample.
        nested (SampleClass, optional): A nested SampleClass object. Defaults to None.
        nested_list (list[SampleClass], optional): A list of nested SampleClass objects. Defaults to an empty list.
    """

    def __init__(self, name, value, nested=None, nested_list=None):
        self.name = name
        self.value = value
        self.nested = nested
        self.nested_list = nested_list or []


class TestSerializer:
    def test_serialize_int(self):
        assert Serializer.serialize_value(123) == 123

    def test_serialize_float(self):
        assert Serializer.serialize_value(123.45) == 123.45

    def test_serialize_str(self):
        assert Serializer.serialize_value("test") == "test"

    def test_serialize_bool(self):
        assert Serializer.serialize_value(True) == True

    def test_serialize_none(self):
        assert Serializer.serialize_value(None) == None

    def test_serialize_date(self):
        date = datetime(2023, 10, 5, 14, 30, 0)
        expected = "2023-10-05 14:30:00"
        assert Serializer.serialize_value(date) == expected

    def test_serialize_enum(self):
        assert Serializer.serialize_value(SampleEnum.VALUE1) == "value1"

    def test_serialize_list(self):
        data = [1, "test", 3.14]
        expected = [1, "test", 3.14]
        assert Serializer.serialize_value(data) == expected

    def test_serialize_dict(self):
        data = {"key1": 1, "key2": "value"}
        expected = {"key1": 1, "key2": "value"}
        assert Serializer.serialize_value(data) == expected

    def test_serialize_object(self):
        obj = SampleClass("test", 123)
        expected = {"name": "test", "value": 123, "nested": None, "nested_list": []}
        assert Serializer.to_dict(obj) == expected

    def test_to_json(self):
        obj = SampleClass("test", 123)
        expected = '{"name": "test", "value": 123, "nested": null, "nested_list": []}'
        assert Serializer.to_json(obj) == expected

    def test_from_dict(self):
        data = {"name": "test", "value": 123}
        obj = Serializer.from_dict(SampleClass, data)
        assert obj.name == "test"
        assert obj.value == 123

    def test_serialize_complex_nested_object(self):
        nested_obj1 = SampleClass("nested1", 456)
        nested_obj2 = SampleClass("nested2", 789)
        obj = SampleClass("test", 123, nested=nested_obj1, nested_list=[nested_obj1, nested_obj2])
        expected = {
            "name": "test",
            "value": 123,
            "nested": {"name": "nested1", "value": 456, "nested": None, "nested_list": []},
            "nested_list": [
                {"name": "nested1", "value": 456, "nested": None, "nested_list": []},
                {"name": "nested2", "value": 789, "nested": None, "nested_list": []},
            ],
        }
        assert Serializer.to_dict(obj) == expected

    def test_serialize_datetime(self):
        date = datetime(2023, 10, 5, 14, 30, 0)
        expected = "2023-10-05 14:30:00"
        assert Serializer.serialize_value(date) == expected

    def test_serialize_str_date(self):
        date_str = "2023-10-05 14:30:00"
        expected = "2023-10-05 14:30:00"
        assert Serializer.serialize_value(date_str) == expected

    def test_serialize_list_dates(self):
        dates = [datetime(2023, 10, 5, 14, 30, 0), datetime(2023, 10, 6, 15, 45, 0)]
        expected = ["2023-10-05 14:30:00", "2023-10-06 15:45:00"]
        assert Serializer.serialize_value(dates) == expected

    def test_serialize_dict_dates(self):
        dates = {"start": datetime(2023, 10, 5, 14, 30, 0), "end": datetime(2023, 10, 6, 15, 45, 0)}
        expected = {"start": "2023-10-05 14:30:00", "end": "2023-10-06 15:45:00"}
        assert Serializer.serialize_value(dates) == expected

    def test_serialize_invalid_date_str(self, caplog):
        invalid_date_str = "invalid date"
        with caplog.at_level("WARNING"):
            result = Serializer.serialize_date(invalid_date_str)
            assert result == invalid_date_str
            assert any("Failed to parse date string" in message for message in caplog.messages)

    def test_serialize_period(self):
        period = Period(start=datetime(2023, 10, 5, 14, 30, 0), end=datetime(2023, 10, 6, 15, 45, 0))
        expected = {"start": "2023-10-05 14:30:00", "end": "2023-10-06 15:45:00"}
        assert Serializer.serialize_value(period) == expected

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
        assert Serializer.serialize_value(periods) == expected

    def test_is_date(self):
        assert Serializer.is_date(datetime.now())
        assert not Serializer.is_date("not a date")

    def test_parse(self):
        date_str = "2023-01-01 00:00:00"
        parsed_date = Serializer.parse_date(date_str)
        assert parsed_date == datetime(2023, 1, 1, 0, 0, 0)
        assert Serializer.parse_date("invalid date") is None
