import math
from collections.abc import Sequence
from dataclasses import dataclass

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException


@dataclass(frozen=True)
class CurveLabels:
    subject: str
    x: str
    y: str


def validate_curve(xs: Sequence[float], ys: Sequence[float], labels: CurveLabels) -> None:
    _check_equal_length(xs, ys, labels)
    _check_at_least_two_points(xs, labels)
    _check_finite(xs, ys, labels)
    _check_non_negative_strictly_increasing_x(xs, labels)


def _check_equal_length(xs: Sequence[float], ys: Sequence[float], labels: CurveLabels) -> None:
    if len(xs) != len(ys):
        raise EcalcValidationException(
            f"Need equal number of {labels.x} and {labels.y} values for {labels.subject}. "
            f"Got {len(xs)} {labels.x} values and {len(ys)} {labels.y} values."
        )


def _check_at_least_two_points(xs: Sequence[float], labels: CurveLabels) -> None:
    if len(xs) < 2:
        raise EcalcValidationException(f"Need at least two {labels.x}/{labels.y} points for {labels.subject}.")


def _check_finite(xs: Sequence[float], ys: Sequence[float], labels: CurveLabels) -> None:
    if not all(math.isfinite(value) for value in [*xs, *ys]):
        raise EcalcValidationException(
            f"The {labels.x} and {labels.y} values for {labels.subject} must be finite numbers."
        )


def _check_non_negative_strictly_increasing_x(xs: Sequence[float], labels: CurveLabels) -> None:
    if xs[0] < 0 or any(later <= earlier for earlier, later in zip(xs, xs[1:])):
        raise EcalcValidationException(
            f"The {labels.x} values for {labels.subject} must be non-negative and strictly increasing, so the curve can be interpolated."
        )
