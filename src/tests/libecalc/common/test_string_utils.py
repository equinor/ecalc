import pytest
from libecalc.common.string_utils import generate_id, get_duplicates, to_camel_case


class TestGetDuplicates:
    def test_no_duplicates(self):
        assert get_duplicates(["name1", "name2", "name3"]) == set()

    def test_duplicates(self):
        assert get_duplicates(["name1", "name2", "name1"]) == {"name1"}


class TestGenerateId:
    def test_single_string(self):
        assert isinstance(generate_id("some_name"), str)

    def test_multiple_strings(self):
        assert isinstance(generate_id("some_prefix", "some_type", "some_name"), str)


test_data = [
    # "snake_case, camel_case"
    ("my_camel_case", "myCamelCase"),
    ("m_c", "mC"),
    ("m_C", "mC"),
    ("M_C", "MC"),
    ("_C", "C"),
    ("_c", "c"),
    ("m_", "m"),
    ("M_", "M"),
    ("my_cAmeLCase", "myCAmeLCase"),
]


class TestToCamelCase:
    @pytest.mark.parametrize("snake_case, camel_case", test_data)
    def test_to_camel_case(self, snake_case: str, camel_case: str):
        assert to_camel_case(snake_case) == camel_case
