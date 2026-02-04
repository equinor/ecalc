from libecalc.domain.process.entities.process_units.compressor_stage import CompressorStage
from libecalc.domain.process.entities.process_units.recirculation_loop import RecirculationLoop
from libecalc.domain.process.process_solver.solver import Solver
from libecalc.domain.process.process_system.process_system import ProcessSystem
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class RecirculationSolver(Solver):
    def __init__(self, recirculation_loop: RecirculationLoop):
        self._recirculation_loop = recirculation_loop

    def solve(self, process_system: ProcessSystem, inlet_stream: FluidStream) -> FluidStream | None:
        inner_process = self._recirculation_loop.get_inner_process()
        if isinstance(inner_process, CompressorStage):
            minimum_rate = inner_process.get_minimum_rate()
        else:
            compressors = inner_process.get_process_units()
            minimum_rates = [compressor.get_minimum_rate() for compressor in compressors]
            minimum_rate = max(minimum_rates)

        self._recirculation_loop.set_inner_rate(minimum_rate)
        return process_system.propagate_stream(inlet_stream=inlet_stream)
