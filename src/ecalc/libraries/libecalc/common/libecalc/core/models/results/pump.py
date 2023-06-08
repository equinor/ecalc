from __future__ import annotations

from typing import List, Optional

from libecalc.core.models.results.base import EnergyFunctionResult


class PumpModelResult(EnergyFunctionResult):
    rate: List[Optional[float]]
    suction_pressure: List[Optional[float]]
    discharge_pressure: List[Optional[float]]
    fluid_density: List[Optional[float]]
    operational_head: List[Optional[float]]
