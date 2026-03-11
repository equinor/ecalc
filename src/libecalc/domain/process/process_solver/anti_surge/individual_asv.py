from libecalc.domain.process.entities.process_units.recirculation_loop import RecirculationLoop
from libecalc.domain.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeStrategy
from libecalc.domain.process.process_system.compressor_stage_process_unit import CompressorStageProcessUnit
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
        *,
        recirculation_loops: list[RecirculationLoop],
        compressors: list[CompressorStageProcessUnit],
    ):
        assert len(recirculation_loops) == len(compressors)
        self._recirculation_loops = recirculation_loops
        self._compressors = compressors

    def apply(self, inlet_stream: FluidStream) -> FluidStream:
        current_stream = inlet_stream
        for loop, compressor in zip(self._recirculation_loops, self._compressors, strict=True):
            boundary = compressor.get_recirculation_range(inlet_stream=current_stream)
            loop.set_recirculation_rate(boundary.min)
            current_stream = loop.propagate_stream(inlet_stream=current_stream)

        return current_stream
