from libecalc.domain.process.compressor.core.train.utils.common import EPSILON
from libecalc.domain.process.entities.process_units.recirculation_loop import RecirculationLoop
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_system.compressor_stage_process_unit import CompressorStageProcessUnit
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


def get_recirculation_rate_boundary(compressor: CompressorStageProcessUnit, inlet_stream: FluidStream) -> Boundary:
    """Compute recirculation boundary from compressor capacity at current speed and inlet."""
    max_rate = compressor.get_maximum_standard_rate(inlet_stream=inlet_stream) * (1 - EPSILON)
    min_rate = compressor.get_minimum_standard_rate(inlet_stream=inlet_stream) * (1 + EPSILON)
    return Boundary(
        min=max(0.0, min_rate - inlet_stream.standard_rate_sm3_per_day),
        max=max(0.0, max_rate - inlet_stream.standard_rate_sm3_per_day),
    )


def max_recirculation_pressure(
    recirculation_loops: list[RecirculationLoop],
    compressors: list[CompressorStageProcessUnit],
    inlet_stream: FluidStream,
) -> float:
    """Propagate with maximum recirculation on every stage to find lowest achievable pressure."""
    current_stream = inlet_stream
    for loop, compressor in zip(recirculation_loops, compressors):
        boundary = get_recirculation_rate_boundary(compressor, current_stream)
        loop.set_recirculation_rate(boundary.max)
        current_stream = loop.propagate_stream(inlet_stream=current_stream)
    return current_stream.pressure_bara
