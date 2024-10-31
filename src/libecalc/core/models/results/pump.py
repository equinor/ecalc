from __future__ import annotations

from typing import Optional

from libecalc.core.models.results.base import EnergyFunctionResult


class PumpModelResult(EnergyFunctionResult):
    rate: list[Optional[float]]
    suction_pressure: list[Optional[float]]
    discharge_pressure: list[Optional[float]]
    fluid_density: list[Optional[float]]
    operational_head: list[Optional[float]]
