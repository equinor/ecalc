from collections.abc import Hashable, Iterable, Sequence
from itertools import pairwise

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.common.time_utils import Period
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


class InvalidEcalcModelException(EcalcValidationException):
    pass


def require_name(name: str, subject: str) -> None:
    if not name.strip():
        raise InvalidEcalcModelException(f"{subject} name must not be empty.")


def require_sequential_periods(periods: Sequence[Period], subject: str) -> None:
    if not periods:
        raise InvalidEcalcModelException(f"{subject} must have at least one period.")
    for previous, current in pairwise(periods):
        if previous.end != current.start:
            raise InvalidEcalcModelException(
                f"{subject} periods must be sequential without gaps or overlaps, got {previous} followed by {current}."
            )


def require_unique[T: Hashable](values: Iterable[T], subject: str) -> None:
    seen: set[T] = set()
    for value in values:
        if value in seen:
            raise InvalidEcalcModelException(f"{subject} must be unique, got duplicate '{value}'.")
        seen.add(value)


def require_positive(expression: TimeSeriesExpression, subject: str) -> list[float]:
    values = expression.get_masked_values()
    for period, value in zip(expression.get_periods(), values, strict=True):
        if not value > 0:
            raise InvalidEcalcModelException(
                f"{subject} must be greater than 0, got {value} in {period} for '{expression.get_original_expression()}'."
            )
    return values


def require_periods(actual: Sequence[Period], expected: Sequence[Period], subject: str) -> None:
    if list(actual) != list(expected):
        raise InvalidEcalcModelException(f"{subject} must be defined for the same periods as the simulation.")
