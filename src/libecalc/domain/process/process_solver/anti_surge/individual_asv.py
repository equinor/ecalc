from libecalc.domain.process.entities.process_units.recirculation_loop import RecirculationLoop
from libecalc.domain.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeStrategy
from libecalc.domain.process.process_solver.process_simulator import Configuration, ProcessSimulator
from libecalc.domain.process.process_solver.solvers.recirculation_solver import RecirculationConfiguration
from libecalc.domain.process.process_system.compressor_stage_process_unit import CompressorStageProcessUnit
from libecalc.domain.process.process_system.process_system import ProcessSystemId
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class IndividualASVAntiSurgeStrategy(AntiSurgeStrategy):
    """Anti-surge strategy for INDIVIDUAL ASV topology (one recirculation loop per stage).

    Propagates stage-by-stage, setting each stage’s ASV recirculation to the minimum feasible
    value based on that stage’s actual inlet stream, and returns the final outlet stream.

    Contract:
      - Mutates each stage's RecirculationLoop by setting its recirculation rate.
      - Returns the outlet stream after all stages have been propagated with minimum feasible recirculation.
    """

    def __init__(
        self,
        recirculation_loops: list[RecirculationLoop],
        compressors: list[CompressorStageProcessUnit],
        simulator: ProcessSimulator,
    ):
        assert len(recirculation_loops) == len(compressors)
        self._recirculation_loop_ids = [recirculation_loop.get_id() for recirculation_loop in recirculation_loops]
        self._compressors = compressors
        self._simulator = simulator

    def _apply_recirculation_configuration(self, loop_id: ProcessSystemId, recirculation_rate: float):
        self._simulator.apply_configuration(
            Configuration(
                simulation_unit_id=loop_id,
                value=RecirculationConfiguration(
                    recirculation_rate=recirculation_rate,
                ),
            )
        )

    def reset(self) -> None:
        for loop_id in self._recirculation_loop_ids:
            self._apply_recirculation_configuration(loop_id=loop_id, recirculation_rate=0)

    def apply(self, inlet_stream: FluidStream) -> FluidStream:
        for loop_id, compressor in zip(self._recirculation_loop_ids, self._compressors, strict=True):
            current_stream = self._simulator.simulate(to_id=loop_id)
            boundary = compressor.get_recirculation_range(inlet_stream=current_stream)
            self._apply_recirculation_configuration(loop_id=loop_id, recirculation_rate=boundary.min)

        return self._simulator.simulate()
