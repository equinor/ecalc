from dataclasses import dataclass
from math import isclose, isfinite

from libecalc.process.tolerances import PRESSURE_CALCULATION_TOLERANCE


def _validate_tolerance(value: float) -> None:
    if not isfinite(value) or value < 0:
        raise ValueError(f"Tolerance must be finite and non-negative, got {value}.")


@dataclass(frozen=True)
class RelativeTolerance:
    value: float

    def __post_init__(self):
        _validate_tolerance(self.value)

    def is_close(self, a: float, b: float) -> bool:
        return isclose(a, b, rel_tol=self.value, abs_tol=0)


@dataclass(frozen=True)
class AbsoluteTolerance:
    value: float

    def __post_init__(self):
        _validate_tolerance(self.value)

    def is_close(self, a: float, b: float) -> bool:
        return isclose(a, b, rel_tol=0, abs_tol=self.value)


Tolerance = RelativeTolerance | AbsoluteTolerance


class FloatConstraint:
    def __init__(self, value, tolerance: Tolerance | None = None):
        self.value = float(value)
        self.tolerance: Tolerance = (
            RelativeTolerance(PRESSURE_CALCULATION_TOLERANCE) if tolerance is None else tolerance
        )

    def with_value(self, value) -> "FloatConstraint":
        """New constraint with the same tolerance."""
        return FloatConstraint(value, self.tolerance)

    def _is_close(self, other):
        try:
            other_val = float(other)
        except (TypeError, ValueError):
            return NotImplemented

        return self.tolerance.is_close(self.value, other_val)

    def __eq__(self, other):
        return self._is_close(other)

    def __ne__(self, other):
        return not self._is_close(other)

    def __lt__(self, other):
        try:
            other_val = float(other)
        except (TypeError, ValueError):
            return NotImplemented
        # a < b if a is not close to b and a < b
        return not self._is_close(other) and self.value < other_val

    def __le__(self, other):
        try:
            float(other)
        except (TypeError, ValueError):
            return NotImplemented
        # a <= b if a < b or a approx equal to b
        return self.__lt__(other) or self._is_close(other)

    def __gt__(self, other):
        try:
            other_val = float(other)
        except (TypeError, ValueError):
            return NotImplemented
        # a > b if a is not close to b and a > b
        return not self._is_close(other) and self.value > other_val

    def __ge__(self, other):
        try:
            float(other)
        except (TypeError, ValueError):
            return NotImplemented
        # a >= b if a > b or a approx equal to b
        return self.__gt__(other) or self._is_close(other)

    def __repr__(self):
        return f"FloatConstraint({self.value}, {self.tolerance})"
