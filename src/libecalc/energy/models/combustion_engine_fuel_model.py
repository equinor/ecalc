from __future__ import annotations

import math
from collections.abc import Sequence

import numpy as np

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.energy.models.curve_validation import CurveLabels, validate_curve

SECONDS_PER_DAY = 86400


def _fuel_for_power(loads: np.ndarray, efficiencies: np.ndarray, lower_heating_value: float, power: float) -> float:
    assert power >= 0, f"Power must not be negative, got {power}."
    if power == 0:
        return 0.0
    # Below the first load the engine burns the fuel of the first load. Above the last, the last efficiency is used.
    load = max(power, float(loads[0]))
    efficiency = float(np.interp(load, loads, efficiencies))
    return load * SECONDS_PER_DAY / lower_heating_value / efficiency


class TurbineFuelModel:
    """Fuel consumption [Sm3/day] of a gas turbine from a load [MW] and efficiency curve."""

    def __init__(self, loads: Sequence[float], efficiencies: Sequence[float], lower_heating_value: float) -> None:
        validate_combustion_engine_curve(loads, efficiencies, subject="gas turbine")
        validate_lower_heating_value(lower_heating_value, subject="gas turbine")
        self._lower_heating_value = lower_heating_value
        self._loads = np.asarray(loads, dtype=np.float64)
        self._efficiencies = np.asarray(efficiencies, dtype=np.float64)

    @property
    def max_power(self) -> float:
        return float(self._loads[-1])

    @property
    def loads(self) -> list[float]:
        return self._loads.tolist()

    @property
    def efficiencies(self) -> list[float]:
        return self._efficiencies.tolist()

    @property
    def lower_heating_value(self) -> float:
        return self._lower_heating_value

    def fuel_for_power(self, power: float) -> float:
        return _fuel_for_power(self._loads, self._efficiencies, self._lower_heating_value, power)


class DieselEngineFuelModel:
    """Fuel consumption [L/day] of a diesel engine from a load [MW] and efficiency curve."""

    def __init__(self, loads: Sequence[float], efficiencies: Sequence[float], lower_heating_value: float) -> None:
        validate_combustion_engine_curve(loads, efficiencies, subject="diesel engine")
        validate_lower_heating_value(lower_heating_value, subject="diesel engine")
        self._lower_heating_value = lower_heating_value
        self._loads = np.asarray(loads, dtype=np.float64)
        self._efficiencies = np.asarray(efficiencies, dtype=np.float64)

    @property
    def max_power(self) -> float:
        return float(self._loads[-1])

    @property
    def loads(self) -> list[float]:
        return self._loads.tolist()

    @property
    def efficiencies(self) -> list[float]:
        return self._efficiencies.tolist()

    @property
    def lower_heating_value(self) -> float:
        return self._lower_heating_value

    def fuel_for_power(self, power: float) -> float:
        return _fuel_for_power(self._loads, self._efficiencies, self._lower_heating_value, power)


CombustionEngineFuelModel = TurbineFuelModel | DieselEngineFuelModel


def validate_combustion_engine_curve(loads: Sequence[float], efficiencies: Sequence[float], subject: str) -> None:
    validate_curve(loads, efficiencies, CurveLabels(subject=subject, x="load", y="efficiency"))
    invalid = [(load, efficiency) for load, efficiency in zip(loads, efficiencies) if not 0 < efficiency <= 1]
    if invalid:
        load, efficiency = invalid[0]
        raise EcalcValidationException(
            f"{subject.capitalize()} efficiencies must be fractions above 0 and up to 1. Got {efficiency} at load "
            f"{load}. Remove points with zero efficiency, such as a zero-load point."
        )


def validate_lower_heating_value(lower_heating_value: float, subject: str) -> None:
    if not math.isfinite(lower_heating_value) or lower_heating_value <= 0:
        raise EcalcValidationException(f"{subject.capitalize()} lower heating value must be finite and greater than 0.")
