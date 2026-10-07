from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.energy.models.curve_validation import CurveLabels, validate_curve


class GeneratorSetFuelModel:
    """Generator set fuel consumption [Sm3/day] from the electrical power [MW], interpolated from a curve."""

    def __init__(self, powers: Sequence[float], fuels: Sequence[float]) -> None:
        validate_generator_set_curve(powers, fuels)
        self._powers = np.asarray(powers, dtype=np.float64)
        self._fuels = np.asarray(fuels, dtype=np.float64)

    @property
    def max_power(self) -> float:
        return float(self._powers[-1])

    def fuel_for_power(self, power: float) -> float:
        assert power >= 0, f"Power must not be negative, got {power}."
        if power == 0:
            return 0.0
        # Same as the legacy generator set: outside the curve the lowest and highest fuel are used
        return float(np.interp(power, self._powers, self._fuels, left=self._fuels.min(), right=self._fuels.max()))


_GENERATOR_SET_LABELS = CurveLabels(subject="generator set", x="power", y="fuel")


def validate_generator_set_curve(powers: Sequence[float], fuels: Sequence[float]) -> None:
    validate_curve(powers, fuels, _GENERATOR_SET_LABELS)
    if any(fuel < 0 for fuel in fuels):
        raise EcalcValidationException("Generator set fuel must not be negative.")
