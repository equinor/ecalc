import abc

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.propagation_failure import PropagationFailure


class StreamPropagator(abc.ABC):
    @abc.abstractmethod
    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream | PropagationFailure: ...
