from collections.abc import Sequence
from typing import Final

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_error import RateTooLowError
from libecalc.process.process_pipeline.process_unit import ProcessUnitId
from libecalc.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeStrategy
from libecalc.process.process_solver.configuration import Configuration, OperatingConfiguration
from libecalc.process.process_solver.process_runner import ProcessRunner
from libecalc.process.process_solver.solver import Solution


class MinimumFlowProtectedProcessRunner(ProcessRunner):
    def __init__(
        self,
        runner: ProcessRunner,
        anti_surge_strategy: AntiSurgeStrategy,
    ) -> None:
        self._runner: Final = runner
        self._anti_surge_strategy: Final = anti_surge_strategy
        self._last_protection: Solution[Sequence[Configuration]] | None = None

    @property
    def anti_surge_strategy(self) -> AntiSurgeStrategy:
        return self._anti_surge_strategy

    def apply_configuration(self, configuration: Configuration[OperatingConfiguration]) -> None:
        self._runner.apply_configuration(configuration)

    def reset_to(self, configurations: Sequence[Configuration] = ()) -> None:
        self._last_protection = None
        self._runner.reset_to(configurations=configurations)

    def run(self, inlet_stream: FluidStream, to_id: ProcessUnitId | None = None) -> FluidStream:
        self._last_protection = None
        try:
            return self._runner.run(inlet_stream=inlet_stream, to_id=to_id)
        except RateTooLowError:
            protection = self._anti_surge_strategy.apply(inlet_stream=inlet_stream)
            self._last_protection = protection
            self._runner.apply_configurations(protection.configuration)
            return self._runner.run(inlet_stream=inlet_stream, to_id=to_id)

    def get_last_protection(self) -> Solution[Sequence[Configuration]] | None:
        return self._last_protection
