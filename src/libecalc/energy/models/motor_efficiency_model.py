from __future__ import annotations

from collections.abc import Sequence

import numpy as np

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.energy.models.curve_validation import CurveLabels, validate_curve


class MotorEfficiencyModel:
    def __init__(self, loads: Sequence[float], efficiencies: Sequence[float]) -> None:
        validate_motor_curve(loads, efficiencies)
        self._loads = np.asarray(loads, dtype=np.float64)
        self._efficiencies = np.asarray(efficiencies, dtype=np.float64)

    def electrical_for_mechanical(self, power: float) -> float:
        return power / float(np.interp(power, self._loads, self._efficiencies))


_MOTOR_LABELS = CurveLabels(subject="motor", x="load", y="efficiency")


def validate_motor_curve(loads: Sequence[float], efficiencies: Sequence[float]) -> None:
    validate_curve(loads, efficiencies, _MOTOR_LABELS)
    invalid = [(load, efficiency) for load, efficiency in zip(loads, efficiencies) if not 0 < efficiency <= 1]
    if invalid:
        load, efficiency = invalid[0]
        raise EcalcValidationException(
            f"Motor efficiencies must be fractions above 0 and up to 1. Got {efficiency} at load {load}."
        )
