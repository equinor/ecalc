from __future__ import annotations

import numpy as np
from scipy.interpolate import interp1d

from libecalc.energy.models.convex_hull import FloatArray


class FuelPowerCurve:
    """A compressor's sampled (fuel, power) relation, invertible in either direction."""

    def __init__(self, sorted_fuel: FloatArray, sorted_power: FloatArray) -> None:
        self._power_to_fuel = interp1d(
            sorted_power, sorted_fuel, fill_value=(sorted_fuel[0], np.nan), bounds_error=False
        )
        self._fuel_to_power = interp1d(
            sorted_fuel, sorted_power, fill_value=(sorted_power[0], np.nan), bounds_error=False
        )

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
