from datetime import datetime
from typing import Optional, TypeVar

import pytest

from libecalc.common.errors.exceptions import (
    DifferentLengthsError,
    EcalcError,
    IncompatibleDataError,
    MissingKeyError,
)
from libecalc.common.math.math_utils import MathUtil

T = TypeVar("T")


@pytest.mark.parametrize(
    "what, this, that, expected_result, expected_exception",
    [
        (
            "incorrect lengths",
            {datetime(2024, 1, 4): 1, datetime(2020, 1, 1): 2, datetime(2021, 1, 1): 3, datetime(2023, 3, 1): 4},
            {datetime(2024, 1, 4): 1, datetime(2020, 1, 1): 2, datetime(2021, 1, 1): 3},
            None,
            (DifferentLengthsError, "Subtracting values A-B failed due to different vector lengths."),
        ),
        (
            "mismatching keys",
            {datetime(2024, 1, 4): 1, datetime(2020, 1, 1): 2, datetime(2021, 1, 1): 3, datetime(2023, 3, 1): 4},
            {datetime(2024, 1, 4): 1, datetime(2020, 1, 1): 2, datetime(2021, 1, 1): 3, datetime(2025, 3, 1): 4},
            None,
            (MissingKeyError, "Subtracting values A-B failed due to missing time step in B."),
        ),
        (
            "same data, all diff results should be zero",
            {datetime(2024, 1, 4): 1, datetime(2020, 1, 1): 2, datetime(2021, 1, 1): 3, datetime(2023, 3, 1): 4},
            {datetime(2024, 1, 4): 1, datetime(2020, 1, 1): 2, datetime(2021, 1, 1): 3, datetime(2023, 3, 1): 4},
            {datetime(2024, 1, 4): 0, datetime(2020, 1, 1): 0, datetime(2021, 1, 1): 0, datetime(2023, 3, 1): 0},
            None,
        ),
        (
            "mix of positive, zero and negative results",
            {
                datetime(2020, 1, 1): 2,
                datetime(2021, 1, 1): 3,
                datetime(2023, 3, 1): 0,
                datetime(2024, 1, 4): 1,
                datetime(2025, 3, 1): -1,
                datetime(2026, 3, 1): -2,
            },
            {
                datetime(2020, 1, 1): 2,
                datetime(2021, 1, 1): 1,
                datetime(2023, 3, 1): 0,
                datetime(2024, 1, 4): 2,
                datetime(2025, 3, 1): -1,
                datetime(2026, 3, 1): -1,
            },
            {
                datetime(2020, 1, 1): 0,
                datetime(2021, 1, 1): 2,
                datetime(2023, 3, 1): 0,
                datetime(2024, 1, 4): -1,
                datetime(2025, 3, 1): 0,
                datetime(2026, 3, 1): -1,
            },
            None,
        ),
        (
            "use string as key",
            {"a": 1, "b": 2, "c": 3, "d": 4},
            {"a": 1, "b": 2, "c": 1, "d": 2},
            {"a": 0, "b": 0, "c": 2, "d": 2},
            None,
        ),
        ("none", None, None, None, (IncompatibleDataError, "A or B is None.")),
        ("empty", {}, {}, {}, None),
    ],
)
def test_elementwise_subtraction_by_key(
    what: str,
    this: dict[T, float],
    that: dict[T, float],
    expected_result: Optional[dict[T, float]],
    expected_exception: Optional[tuple[type[EcalcError], str]],
):
    if expected_result is not None:
        result = MathUtil.elementwise_subtraction_by_key(this, that)
        assert expected_result == result
    elif expected_exception is not None:
        expected_exception_class, expected_exception_text = expected_exception
        with pytest.raises(expected_exception_class) as exc:
            MathUtil.elementwise_subtraction_by_key(this, that)
        assert expected_exception_text in str(exc.value)
    else:
        raise AssertionError()
