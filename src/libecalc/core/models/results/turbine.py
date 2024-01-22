from __future__ import annotations

from typing import List, Optional

import numpy as np

from libecalc.common.units import Unit
from libecalc.core.models.results import EnergyFunctionResult


class TurbineResult(EnergyFunctionResult):
    load: List[Optional[float]]  # MW
    efficiency: List[Optional[float]]  # % Fraction between 0 and 1
    fuel_rate: List[Optional[float]]  # Sm3/day?

    power: List[Optional[float]]
    power_unit: Unit

    exceeds_maximum_load: List[bool]

    @property
    def is_valid(self) -> List[bool]:
        return np.invert(self.exceeds_maximum_load).tolist()
