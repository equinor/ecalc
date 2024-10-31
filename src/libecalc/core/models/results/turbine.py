from __future__ import annotations

from typing import Optional

import numpy as np

from libecalc.common.units import Unit
from libecalc.core.models.results import EnergyFunctionResult


class TurbineResult(EnergyFunctionResult):
    load: list[Optional[float]]  # MW
    efficiency: list[Optional[float]]  # % Fraction between 0 and 1
    fuel_rate: list[Optional[float]]  # Sm3/day?

    power: list[Optional[float]]
    power_unit: Unit

    exceeds_maximum_load: list[bool]

    @property
    def is_valid(self) -> list[bool]:
        return np.invert(self.exceeds_maximum_load).tolist()
