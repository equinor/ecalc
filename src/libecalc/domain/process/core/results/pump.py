from __future__ import annotations

from libecalc.domain.process.core.results.base import EnergyFunctionResult


class PumpModelResult(EnergyFunctionResult):
    rate: list[float]
    suction_pressure: list[float]
    discharge_pressure: list[float]
    fluid_density: list[float]
    operational_head: list[float]
