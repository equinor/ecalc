from __future__ import annotations

import abc
from collections.abc import Callable
from dataclasses import dataclass, field

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_solver.solver import SolverFailure


@dataclass
class Finding[TConfiguration]:
    """Result of a Finder.find() call.

    Always contains a configuration — the found one on success, the closest reached on failure.
    """

    configuration: TConfiguration
    failure: SolverFailure | None = field(default=None)

    @property
    def success(self) -> bool:
        return self.failure is None


class Finder[TConfiguration](abc.ABC):
    @abc.abstractmethod
    def find(
        self,
        func: Callable[[TConfiguration], FluidStream],
    ) -> Finding[TConfiguration]: ...
