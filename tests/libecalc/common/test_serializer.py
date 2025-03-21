from datetime import datetime
from enum import Enum
from libecalc.common.serializer import Serializer


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
