from libecalc.domain.process.entities.process_units.simplified_stream_mixer.simplified_stream_mixer import (
    SimplifiedStreamMixer,
)
from libecalc.domain.process.process_pipeline.process_unit import ProcessUnit, ProcessUnitId
from libecalc.domain.process.value_objects.fluid_stream import FluidService, FluidStream


class Mixer(ProcessUnit):
    """Mixes one external stream into the through-stream.

    The external stream is set via `set_stream` before propagation. This models
    a sidestream injection point in an interstage manifold.
    """

    def __init__(self, fluid_service: FluidService, process_unit_id: ProcessUnitId = ProcessUnit._create_id()):
        self._id = process_unit_id
        self._mixer = SimplifiedStreamMixer(fluid_service)
        self._external_stream: FluidStream | None = None

    def get_id(self) -> ProcessUnitId:
        return self._id

    def set_stream(self, stream: FluidStream) -> None:
        self._external_stream = stream

    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream:
        if self._external_stream is None:
            raise ValueError("Mixer has no external stream set; call set_stream() before propagating.")
        return self._mixer.mix_streams([inlet_stream, self._external_stream])
