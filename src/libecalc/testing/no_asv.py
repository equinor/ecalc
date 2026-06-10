from collections.abc import Sequence
from typing import override

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeStrategy
from libecalc.process.process_solver.configuration import Configuration, RecirculationConfiguration
from libecalc.process.process_solver.solver import Solution


class NoASVAntiSurgeStrategy(AntiSurgeStrategy):
    """No-op anti-surge strategy for tests without a real compressor/ASV setup."""

    @override
    def apply(self, inlet_stream: FluidStream) -> Solution[Sequence[Configuration[RecirculationConfiguration]]]:
        return Solution(success=True, configuration=[])

    @override
    def reset(self) -> None:
        pass
