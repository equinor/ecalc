from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.process.process_solver.configuration import Configuration, RecirculationConfiguration
from libecalc.process.process_solver.solver import Solution, SolverFailure


class AntiSurgeType(StrEnum):
    NO_ASV = "NO_ASV"
    INDIVIDUAL_ASV = "INDIVIDUAL_ASV"
    COMMON_ASV = "COMMON_ASV"


class AntiSurgeStrategy(ABC):
    """
    Strategy for keeping the train within compressor chart capacity at the current speed.

    Used primarily during speed search when propagation may fail (e.g. CompressorSurgeError).
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

    @abstractmethod
    def reset(self) -> None:
        """Zero all recirculation managed by this strategy.

        Called before re-evaluating anti-surge in contexts where stale recirculation
        from a previous evaluation would corrupt the result (e.g. upstream-choke search).
        """
        ...


@dataclass
class NoAntiSurgeControlFailure(SolverFailure):
    source_id: ProcessUnitId
    reason: str = ""


class NoAntiSurgeStrategy(AntiSurgeStrategy):
    """
    TODO: Should this raise error if attempted to be used, because that would mean that
    we need Anti-Surge, but we have no way of handling it.
    """

    def __init__(
        self,
        source_id: ProcessUnitId,
    ):
        self._source_id = source_id

    def reset(self) -> None: ...

    def apply(self, inlet_stream: FluidStream) -> Solution[Sequence[Configuration[RecirculationConfiguration]]]:
        return Solution(
            configuration=[],
            failure=NoAntiSurgeControlFailure(
                source_id=self._source_id, reason="No Anti-Surge protection added when apparently needed."
            ),
        )
