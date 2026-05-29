from __future__ import annotations

from dataclasses import dataclass

from libecalc.domain.process.value_objects.chart.chart import ChartData
from libecalc.process.process_solver.solver_assembly import ProcessSolverSystem

__all__ = ["ProcessSolverSystem", "StageConfig"]


@dataclass(frozen=True)
class StageConfig:
    chart_data: ChartData
    inlet_temperature_kelvin: float = 303.15
    remove_liquid_after_cooling: bool = True
    pressure_drop_ahead_of_stage: float = 0.0
