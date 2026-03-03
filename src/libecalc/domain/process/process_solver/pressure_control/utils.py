from collections.abc import Callable

from libecalc.domain.process.process_solver.pressure_control.types import (
    PressureControlConfiguration,
    RunPressureControlCfg,
)
from libecalc.domain.process.process_solver.solvers.recirculation_solver import RecirculationConfiguration
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


def create_recirculation_eval_func(
    *,
    baseline_cfg: PressureControlConfiguration,
    run_system: RunPressureControlCfg,
) -> Callable[[RecirculationConfiguration], FluidStream]:
    """
    Build an evaluation function for `RecirculationSolver`.

    Keeps everything in `baseline_cfg` fixed (speed/chokes), varies only `recirculation_rate`.
    """

    def func(rcfg: RecirculationConfiguration) -> FluidStream:
        candidate_cfg = PressureControlConfiguration(
            speed=baseline_cfg.speed,
            recirculation_rate=rcfg.recirculation_rate,
            upstream_delta_pressure=baseline_cfg.upstream_delta_pressure,
            downstream_delta_pressure=baseline_cfg.downstream_delta_pressure,
        )
        return run_system(candidate_cfg)

    return func
