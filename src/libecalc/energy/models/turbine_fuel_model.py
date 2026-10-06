from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.energy.models.curve_validation import CurveLabels, validate_curve

SECONDS_PER_DAY = 86400


class TurbineFuelModel:
    """Gas turbine fuel consumption [Sm3/day] from a load [MW] and efficiency curve."""

    def __init__(
        self,
        loads: Sequence[float],
        efficiencies: Sequence[float],
        lower_heating_value: float,
    ) -> None:
        validate_turbine_curve(loads, efficiencies, lower_heating_value)
        self._lower_heating_value = lower_heating_value
        self._loads = np.asarray(loads, dtype=np.float64)
        self._efficiencies = np.asarray(efficiencies, dtype=np.float64)

    @property
    def max_power(self) -> float:
        return float(self._loads[-1])

    def fuel_for_power(self, power: float) -> float:
        assert power >= 0, f"Power must not be negative, got {power}."
        if power == 0:
            return 0.0
        # Below the first load the turbine burns the fuel of the first load. Above the last, the last efficiency is used.
        load = max(power, float(self._loads[0]))
        efficiency = float(np.interp(load, self._loads, self._efficiencies))
        return load * SECONDS_PER_DAY / self._lower_heating_value / efficiency


_TURBINE_LABELS = CurveLabels(subject="turbine", x="load", y="efficiency")


def validate_turbine_curve(loads: Sequence[float], efficiencies: Sequence[float], lower_heating_value: float) -> None:
    validate_curve(loads, efficiencies, _TURBINE_LABELS)
    if any(not 0 <= efficiency <= 1 for efficiency in efficiencies):
        raise EcalcValidationException("Turbine efficiencies must be fractions between 0 and 1.")
    if any(efficiency == 0 and load > 0 for load, efficiency in zip(loads, efficiencies)):
        raise EcalcValidationException("Turbine efficiency must be greater than 0 for loads above 0.")
    if not math.isfinite(lower_heating_value) or lower_heating_value <= 0:
        raise EcalcValidationException("Turbine lower heating value must be greater than 0.")
