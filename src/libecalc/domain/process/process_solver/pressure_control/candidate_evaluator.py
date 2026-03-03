from collections.abc import Callable
from dataclasses import dataclass

from libecalc.domain.process.process_solver.pressure_control.types import PressureControlConfiguration
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


@dataclass
class CandidateEvaluator:
    configure_system: Callable[[PressureControlConfiguration], None]
    propagate: Callable[[FluidStream], FluidStream]

    def evaluate_candidate(self, candidate: PressureControlConfiguration, *, inlet_stream: FluidStream) -> FluidStream:
        """
        Evaluate one operating-point candidate.

        Steps:
          1) Call `configure_system(candidate)` to apply the candidate settings to the underlying (mutable) system.
          2) Propagate `inlet_stream` through the configured system and return the resulting outlet stream.

        `candidate` is immutable; any state changes happen in the underlying system.
        """
        self.configure_system(candidate)
        return self.propagate(inlet_stream)
