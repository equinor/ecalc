import pytest

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
import pandas as pd
from libecalc.common.serializer import Serializer, DateTimeUtils
from libecalc.common.time_utils import Period, Periods


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

    def __repr__(self):
        return f"SampleClass(name={self.name!r}, value={self.value!r})"  # Avoid nested objects in repr


class SlotClass:
    __slots__ = ["name", "value"]

    def __init__(self, name, value):
        self.name = name
        self.value = value


@dataclass
class DataClassExample:
    name: str
    number: int


class TestSerializer:
    """
    Test cases for the Serializer class.

    This class contains various test methods to ensure the correct functionality
    of the Serializer class, including serialization of primitive types, complex types,
    date handling, special cases such as circular references and unknown types,
    and utility methods.
    """

    # Primitive Types
    def test_serialize_int(self):
        assert Serializer.serialize_value(123) == 123

    def test_serialize_float(self):
        assert Serializer.serialize_value(123.45) == 123.45

    def test_serialize_str(self):
        assert Serializer.serialize_value("test") == "test"

    def test_serialize_bool(self):
        assert Serializer.serialize_value(True) == True

    def test_serialize_none(self):
        assert Serializer.serialize_value(None) is None

    # Complex Types
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

    def test_serialize_slots_object(self):
        obj = SlotClass("slotty", 42)
        expected = {"name": "slotty", "value": 42}
        assert Serializer.to_dict(obj) == expected

    def test_serialize_dataframe(self):
        df = pd.DataFrame([{"a": 1, "b": 2}, {"a": 3, "b": 4}])
        expected = [{"a": 1, "b": 2}, {"a": 3, "b": 4}]
        assert Serializer.serialize_value(df) == expected

    def test_serialize_pandas_series(self):
        series = pd.Series([1, 2, 3], index=["a", "b", "c"])
        expected = {"a": 1, "b": 2, "c": 3}
        assert Serializer.serialize_value(series) == expected

    def test_serialize_dataclass(self):
        obj = DataClassExample("data", 99)
        expected = {"name": "data", "number": 99}
        assert Serializer.to_dict(obj) == expected

    def test_serialize_set_and_tuple(self):
        result = Serializer.serialize_value({1, 2, 3})
        assert sorted(result) == [1, 2, 3]  # sets are unordered

        result = Serializer.serialize_value((4, 5))
        assert result == [4, 5]

    def test_serialize_numpy_scalar_and_array(self):
        import numpy as np

        scalar = np.int64(42)
        result = Serializer.serialize_value(scalar)
        assert result == 42

        array = np.array([1, 2, 3])
        result = Serializer.serialize_value(array)
        assert result == [1, 2, 3]

    def test_serialize_complex_nested_object(self):
        nested_obj1 = SampleClass("nested1", 456)
        nested_obj2 = SampleClass("nested2", 789)
        nested_obj1_copy = SampleClass("nested1", 456, nested=None, nested_list=[])

        obj = SampleClass("test", 123, nested=nested_obj1, nested_list=[nested_obj1_copy, nested_obj2])

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

    # Date Handling
    def test_serialize_date(self):
        date = datetime(2023, 10, 5, 14, 30, 0)
        expected = "2023-10-05 14:30:00"
        assert Serializer.serialize_value(date) == expected

    def test_serialize_str_date(self):
        date_str = "2023-10-05 14:30:00"
        expected = "2023-10-05 14:30:00"
        assert Serializer.serialize_value(date_str) == expected

    def test_serialize_datetime(self):
        date = datetime(2023, 10, 5, 14, 30, 0)
        expected = "2023-10-05 14:30:00"
        assert Serializer.serialize_value(date) == expected

    def test_serialize_list_dates(self):
        dates = [datetime(2023, 10, 5, 14, 30, 0), datetime(2023, 10, 6, 15, 45, 0)]
        expected = ["2023-10-05 14:30:00", "2023-10-06 15:45:00"]
        assert Serializer.serialize_value(dates) == expected

    def test_serialize_dict_dates(self):
        dates = {"start": datetime(2023, 10, 5, 14, 30, 0), "end": datetime(2023, 10, 6, 15, 45, 0)}
        expected = {"start": "2023-10-05 14:30:00", "end": "2023-10-06 15:45:00"}
        assert Serializer.serialize_value(dates) == expected

    def test_serialize_invalid_date_str(self):
        invalid_date_str = "invalid date"
        result = DateTimeUtils.serialize_date(invalid_date_str)
        assert result == invalid_date_str

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
        assert DateTimeUtils.is_date(datetime.now())
        assert not DateTimeUtils.is_date("not a date")

    # Special Cases
    def test_serialize_with_circular_reference(self):
        a = SampleClass("a", 1)
        b = SampleClass("b", 2, nested=a)
        a.nested = b  # circular reference

        result = Serializer.to_dict(a)

        assert result["name"] == "a"
        assert result["value"] == 1
        assert "nested" in result

        nested = result["nested"]
        assert nested["name"] == "b"
        assert nested["value"] == 2

        assert "nested" not in nested

    def test_serialize_unknown_type_uses_str(self):
        class Strange:
            def __str__(self):
                return "strange!"

        result = Serializer.serialize_value(Strange())
        assert result == "strange!"

    def test_to_json_ignores_circular_references_and_preserves_valid_fields(self):
        obj = SampleClass("a", 1)
        obj.nested = obj  # Circular at top level

        json_str = Serializer.to_json(obj)

        # Check valid JSON output, not only "{}"
        assert json_str != "{}"

        # Check that the non-circular fields are included
        assert '"name": "a"' in json_str
        assert '"value": 1' in json_str

        # Check that circular fields are not included
        assert '"nested"' not in json_str

    # Utility Methods
    def test_to_json(self):
        obj = SampleClass("test", 123)
        expected = '{"name": "test", "value": 123, "nested": null, "nested_list": []}'
        assert Serializer.to_json(obj) == expected

    def test_from_dict(self):
        data = {"name": "test", "value": 123}
        obj = Serializer.from_dict(SampleClass, data)
        assert obj.name == "test"
        assert obj.value == 123

    def test_from_dict_raises_value_error_on_none(self):
        with pytest.raises(ValueError) as excinfo:
            Serializer.from_dict(SampleClass, None)
        assert "Cannot deserialize" in str(excinfo.value)

    def test_parse(self):
        date_str = "2023-01-01 00:00:00"
        parsed_date = DateTimeUtils.parse_date(date_str)
        assert parsed_date == datetime(2023, 1, 1, 0, 0, 0)
        assert DateTimeUtils.parse_date("invalid date") is None
