from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.energy.models.curve_validation import CurveLabels, validate_curve


class CurveInterpolator:
    def __init__(self, variable_values: Sequence[float], energy_values: Sequence[float]) -> None:
        validate_curve_interpolator(variable_values, energy_values)
        self._variable_values = np.asarray(variable_values, dtype=np.float64)
        self._energy_values = np.asarray(energy_values, dtype=np.float64)

    def energy_for_variable(self, variable: float) -> float:
        return float(np.interp(variable, self._variable_values, self._energy_values, left=np.nan, right=np.nan))


_CURVE_INTERPOLATOR_LABELS = CurveLabels(subject="curve consumer", x="variable", y="energy")


def validate_curve_interpolator(variable_values: Sequence[float], energy_values: Sequence[float]) -> None:
    validate_curve(variable_values, energy_values, _CURVE_INTERPOLATOR_LABELS)
    if any(energy < 0 for energy in energy_values):
        raise EcalcValidationException("Curve consumer energy values must not be negative.")


__all__ = [
    "CurveInterpolator",
    "validate_curve_interpolator",
]
