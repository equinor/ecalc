from collections.abc import Callable
from dataclasses import dataclass

from libecalc.domain.process.entities.process_units.recirculation_loop import RecirculationLoop
from libecalc.domain.process.process_solver.pressure_control.types import PressureControlConfiguration, RunStage
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


@dataclass
class ProcessSystemRunner:
    configure_system: Callable[[PressureControlConfiguration], None]
    propagate: Callable[[FluidStream], FluidStream]

    def run(self, cfg: PressureControlConfiguration, *, inlet_stream: FluidStream) -> FluidStream:
        """
        Run a single forward simulation of a configured process system.

        Steps:
          1) Apply `cfg` to the underlying (mutable) system (e.g. speed/recirculation/chokes).
          2) Propagate `inlet_stream` through the configured system and return the resulting outlet stream.

        `cfg` is immutable; any state changes happen in the underlying system.
        """
        self.configure_system(cfg)
        return self.propagate(inlet_stream)


def make_run_stage_fns(
    recirculation_loops: list[RecirculationLoop],
    inlet_stream: FluidStream,
) -> list[RunStage]:
    """
    Build one per-stage eval function from a list of RecirculationLoops.
    Each function closes over its loop and the inlet stream for that stage.
    inlet_stream for stage N+1 is estimated as outlet of stage N at recirculation_rate=0.
    """
    fns = []
    current_stream = inlet_stream

    for loop in recirculation_loops:

        def make_fn(recirculation_loop: RecirculationLoop, s: FluidStream) -> RunStage:
            def run_stage(recirculation_rate: float) -> FluidStream:
                recirculation_loop.set_recirculation_rate(recirculation_rate)
                return recirculation_loop.propagate_stream(inlet_stream=s)

            return run_stage

        fns.append(make_fn(loop, current_stream))
        loop.set_recirculation_rate(0.0)
        current_stream = loop.propagate_stream(inlet_stream=current_stream)

    return fns
