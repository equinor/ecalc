from __future__ import annotations

from dataclasses import dataclass

from libecalc.domain.process.value_objects.chart.chart import ChartData
from libecalc.process.process_pipeline.process_pipeline import ProcessPipeline
from libecalc.process.process_solver.outlet_pressure_solver import OutletPressureSolver
from libecalc.process.process_solver.process_runner import ProcessRunner
from libecalc.process.process_solver.recirculation_loop import RecirculationLoop
from libecalc.process.process_units.choke import Choke
from libecalc.process.process_units.compressor import Compressor
from libecalc.process.shaft import VariableSpeedShaft


@dataclass(frozen=True)
class StageConfig:
    chart_data: ChartData
    inlet_temperature_kelvin: float = 303.15
    remove_liquid_after_cooling: bool = True
    pressure_drop_ahead_of_stage: float = 0.0


@dataclass(frozen=True)
class ProcessSolverSystem:
    solver: OutletPressureSolver
    runner: ProcessRunner
    pipeline: ProcessPipeline
    shaft: VariableSpeedShaft
    compressors: tuple[Compressor, ...]
    recirculation_loops: tuple[RecirculationLoop, ...]
    choke: Choke | None
