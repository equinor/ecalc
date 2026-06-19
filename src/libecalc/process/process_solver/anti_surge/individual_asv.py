from collections.abc import Sequence
from typing import override

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeStrategy
from libecalc.process.process_solver.configuration import (
    Configuration,
    ConfigurationHandlerId,
    RecirculationConfiguration,
)
from libecalc.process.process_solver.process_runner import ProcessRunner
from libecalc.process.process_solver.solver import (
    Solution,
)
from libecalc.process.process_units.compressor import Compressor


class IndividualASVAntiSurgeStrategy(AntiSurgeStrategy):
    """Anti-surge strategy for INDIVIDUAL ASV topology (one recirculation loop per stage).

    Propagates stage-by-stage, setting each stage's ASV recirculation to the minimum feasible
    value based on that stage's actual inlet stream, and returns the final outlet stream.

    Contract:
      - Mutates each stage's RecirculationLoop by setting its recirculation rate.
      - Returns the outlet stream after all stages have been propagated with minimum feasible recirculation.
    """

    def __init__(
        self,
        recirculation_loop_ids: Sequence[ConfigurationHandlerId],
        compressors: Sequence[Compressor],
        simulator: ProcessRunner,
    ):
        assert len(recirculation_loop_ids) == len(compressors)
        self._recirculation_loop_ids = recirculation_loop_ids
        self._compressors = compressors
        self._simulator = simulator

    def reset(self) -> None:
        for loop_id in self._recirculation_loop_ids:
            self._simulator.reset_configuration_handler(loop_id)

    @override
    def apply(self, inlet_stream: FluidStream) -> Solution[Sequence[Configuration[RecirculationConfiguration]]]:
        self.reset()
        configurations: Sequence[Configuration[RecirculationConfiguration]] = []
        for loop_id, compressor in zip(self._recirculation_loop_ids, self._compressors, strict=True):
            inlet_stream_compressor = self._simulator.run(inlet_stream=inlet_stream, to_id=compressor.get_id())
            boundary = compressor.get_recirculation_range(inlet_stream=inlet_stream_compressor)
            configuration: Configuration[RecirculationConfiguration] = Configuration(
                configuration_handler_id=loop_id,
                value=RecirculationConfiguration(
                    recirculation_rate=boundary.min,
                ),
            )
            configurations.append(configuration)
            self._simulator.apply_configuration(configuration)

        return Solution(
            configuration=configurations,
        )
