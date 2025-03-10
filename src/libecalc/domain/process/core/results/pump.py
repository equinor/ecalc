from __future__ import annotations

from libecalc.domain.process.core.results.base import EnergyFunctionResult


class PumpModelResult(EnergyFunctionResult):
    rate: list[float | None]
    suction_pressure: list[float | None]
    discharge_pressure: list[float | None]
    fluid_density: list[float | None]
    operational_head: list[float | None]
