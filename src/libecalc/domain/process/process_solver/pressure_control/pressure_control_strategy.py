from abc import ABC, abstractmethod
from collections.abc import Sequence

from libecalc.domain.process.process_solver.configuration import Configuration
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.solver import Solution
from libecalc.domain.process.process_solver.solvers.downstream_choke_solver import ChokeConfiguration
from libecalc.domain.process.process_solver.solvers.recirculation_solver import RecirculationConfiguration
from libecalc.domain.process.value_objects.stream_protocol import StreamWithPressure


class PressureControlStrategy(ABC):
    """Strategy for meeting a target outlet pressure at fixed speed.

    Works for both compressor trains (via ASV/choke) and pump systems (via bypass).
    """

    @abstractmethod
    def apply(
        self,
        target_pressure: FloatConstraint,
        inlet_stream: StreamWithPressure,
    ) -> Solution[Sequence[Configuration[RecirculationConfiguration | ChokeConfiguration]]]:
        """Adjust the system to meet the target pressure."""
        ...
