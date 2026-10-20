from __future__ import annotations

from collections.abc import Sequence

import numpy as np
from scipy.interpolate import interp1d


class FuelPowerCurve:
    """A compressor's sampled (fuel, power) relation, invertible in either direction."""

    def __init__(self, sorted_fuel: Sequence[float], sorted_power: Sequence[float]) -> None:
        self._sorted_fuel = np.asarray(sorted_fuel, dtype=np.float64)
        self._sorted_power = np.asarray(sorted_power, dtype=np.float64)
        self._power_to_fuel = interp1d(
            self._sorted_power, self._sorted_fuel, fill_value=(self._sorted_fuel[0], np.nan), bounds_error=False
        )
        self._fuel_to_power = interp1d(
            self._sorted_fuel, self._sorted_power, fill_value=(self._sorted_power[0], np.nan), bounds_error=False
        )

    @property
    def sorted_fuel(self) -> list[float]:
        return self._sorted_fuel.tolist()

    @property
    def sorted_power(self) -> list[float]:
        return self._sorted_power.tolist()

    def fuel_for_power(self, power: float) -> float:
        if power <= 0:
            return 0.0
        return float(np.asarray(self._power_to_fuel(np.asarray([power], dtype=np.float64)), dtype=np.float64)[0])

    def power_for_fuel(self, fuel: float) -> float:
        if fuel <= 0:
            return 0.0
        return float(np.asarray(self._fuel_to_power(np.asarray([fuel], dtype=np.float64)), dtype=np.float64)[0])


__all__ = [
    "FuelPowerCurve",
]
