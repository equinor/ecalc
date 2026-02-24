from math import isclose


class FloatConstraint:
    def __init__(self, value, abs_tol=0.0):
        self.value = float(value)
        self.abs_tol = abs_tol

    def _is_close(self, other):
        try:
            other_val = float(other)
        except (TypeError, ValueError):
            return NotImplemented

        return isclose(self.value, other_val, rel_tol=0, abs_tol=self.abs_tol)

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
        return f"FloatConstraint({self.value}, rel_tol={self.rel_tol}, abs_tol={self.abs_tol})"
