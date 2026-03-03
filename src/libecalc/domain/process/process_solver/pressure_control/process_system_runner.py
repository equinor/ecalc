from collections.abc import Callable
from dataclasses import dataclass

from libecalc.domain.process.process_solver.pressure_control.types import PressureControlConfiguration
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
