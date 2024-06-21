from typing import List, Tuple

import pytest
from libecalc.common.version import Version

data = [
    # negative integers
    (None, Version(0, 0, 0)),
    ("", Version(0, 0, 0)),
    ("weird", Version(0, 0, 0)),
    ("0.0.0", Version(0, 0, 0)),
    ("-1.-2.0", Version(0, 0, 0)),
    ("1.1.1", Version(1, 1, 1)),
    ("10.10.10", Version(10, 10, 10)),
    ("100.100.100", Version(100, 100, 100)),
    ("100.100", Version(100, 100, 0)),
    ("100", Version(100, 0, 0)),
    ("0", Version(0, 0, 0)),
    ("0.1.2", Version(0, 1, 2)),
]


@pytest.mark.parametrize(
    "version_string, expected_version",
    data,
)
def test_versions(version_string, expected_version):
    assert Version.from_string(version_string) == expected_version


version_comparisons = [
    ("1.1.1", "2.1.1"),
    ("2.1.1", "1.1.1"),
    ("1.1.1", "1.2.1"),
    ("1.2.1", "1.1.1"),
    ("1.1.1", "1.1.2"),
    ("1.1.2", "1.1.1"),
    ("1.1.1", "1.1.1"),
    ("100.1.1", "1.1.1"),
    ("1.1.1", "1.1.111"),
]


def combine(test_cases, expected):
    return [test_case + (expected,) for test_case, expected in zip(test_cases, expected)]


def to_version_obj(versions: List[Tuple[str, str]]) -> List[Tuple[Version, Version]]:
    return [(Version.from_string(first), Version.from_string(second)) for first, second in versions]


version_obj_comparisons = to_version_obj(version_comparisons)

less_than_expected = [
    True,
    False,
    True,
    False,
    True,
    False,
    False,
    False,
    True,
]


@pytest.mark.parametrize("first, second, expected", combine(version_obj_comparisons, less_than_expected))
def test_comparison_less_than(first, second, expected):
    assert (first < second) == expected


greater_than_expected = [
    False,
    True,
    False,
    True,
    False,
    True,
    False,
    True,
    False,
]


@pytest.mark.parametrize("first, second, expected", combine(version_obj_comparisons, greater_than_expected))
def test_comparison_grater_than(first, second, expected):
    assert (first > second) == expected


equal_expected = [
    False,
    False,
    False,
    False,
    False,
    False,
    True,
    False,
    False,
]


@pytest.mark.parametrize("first, second, expected", combine(version_obj_comparisons, equal_expected))
def test_comparison_equal(first, second, expected):
    assert (first == second) == expected


@pytest.mark.parametrize("first, second", version_obj_comparisons)
def test_comparison_not_equal(first, second):
    assert (first != second) == (not (first == second))


less_than_or_equal_expected = [
    True,
    False,
    True,
    False,
    True,
    False,
    True,
    False,
    True,
]


@pytest.mark.parametrize("first, second, expected", combine(version_obj_comparisons, less_than_or_equal_expected))
def test_comparison_less_than_or_equal(first, second, expected):
    assert (first <= second) == expected


greater_than_or_equal_expected = [
    False,
    True,
    False,
    True,
    False,
    True,
    True,
    True,
    False,
]


@pytest.mark.parametrize("first, second, expected", combine(version_obj_comparisons, greater_than_or_equal_expected))
def test_comparison_grater_than_or_equal(first, second, expected):
    assert (first >= second) == expected
