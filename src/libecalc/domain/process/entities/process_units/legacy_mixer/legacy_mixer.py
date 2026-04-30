from libecalc.domain.process.entities.process_units.simplified_stream_mixer.simplified_stream_mixer import (
    SimplifiedStreamMixer,
)
from libecalc.process.fluid_stream.fluid_service import FluidService
from libecalc.process.fluid_stream.fluid_stream import FluidStream


class LegacyMixer:
    def __init__(self, number_of_inputs: int, fluid_service: FluidService):
        self.number_of_inputs = number_of_inputs
        self._stream_mixer = SimplifiedStreamMixer(fluid_service)

    def mix_streams(self, streams: list[FluidStream]) -> FluidStream:
        """
        Mixes multiple fluid streams into a single stream.

        Args:
            streams (list[FluidStream]): The list of fluid streams to be mixed.

        Returns:
            FluidStream: The resulting mixed fluid stream.
        """
        if self.number_of_inputs != len(streams):
            raise ValueError("Number of input streams must match the number of inputs defined for the mixer.")

        return self._stream_mixer.mix_streams(streams=streams)
