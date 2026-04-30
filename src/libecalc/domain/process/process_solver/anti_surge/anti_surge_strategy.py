from abc import ABC, abstractmethod
from collections.abc import Sequence

from libecalc.domain.process.process_solver.configuration import Configuration
from libecalc.domain.process.process_solver.solver import Solution
from libecalc.domain.process.process_solver.solvers.recirculation_solver import RecirculationConfiguration
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class AntiSurgeStrategy(ABC):
    """
    Strategy for keeping the train within compressor chart capacity at the current speed.

    Used primarily during speed search when propagation may fail (e.g. RateTooLowError).
    Implementations may adjust control elements (e.g. ASV recirculation) and may
    propagate internally in order to establish a feasible operating point.
    """

    @abstractmethod
    def apply(self, inlet_stream: FluidStream) -> Solution[Sequence[Configuration[RecirculationConfiguration]]]:
        """
        Adjust the system so it can be propagated at the current speed without violating
        minimum-flow / capacity constraints.

        Returns:
            Outlet stream after applying anti-surge adjustments (e.g. setting ASV recirculation).
        """
        ...
