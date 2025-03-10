from __future__ import annotations

import numpy as np

from libecalc.common.units import Unit
from libecalc.domain.process.core.results import EnergyFunctionResult


class TurbineResult(EnergyFunctionResult):
    load: list[float | None]  # MW
    efficiency: list[float | None]  # % Fraction between 0 and 1
    fuel_rate: list[float | None]  # Sm3/day?

    power: list[float | None]
    power_unit: Unit

    exceeds_maximum_load: list[bool]

    @property
    def is_valid(self) -> list[bool]:
        return np.invert(self.exceeds_maximum_load).tolist()
