import pytest
from libecalc.dto.utils.camelcase import to_camel_case

test_data = [
    # "snake_case, camel_case"
    ("my_camel_case", "myCamelCase"),
    ("m_c", "mC"),
    ("m_C", "mC"),
    ("M_C", "MC"),
    # ("_C", "C"),
    # ("_c", "C"),
    # ("m_", "m"),
    # ("M_", "M"),
    ("my_cAmeLCase", "myCAmeLCase"),
]


@pytest.mark.parametrize("snake_case, camel_case", test_data)
def test_to_camel_case(snake_case: str, camel_case: str):
    assert to_camel_case(snake_case) == camel_case
