from libecalc.domain.process.entities.process_units.simplified_stream_mixer.simplified_stream_mixer import (
    SimplifiedStreamMixer,
)
from libecalc.domain.process.value_objects.fluid_stream import FluidServiceInterface, FluidStream


class Mixer:
    def __init__(self, number_of_inputs: int, fluid_service: FluidServiceInterface):
        self.number_of_inputs = number_of_inputs
        self.fluid_service = fluid_service

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

        return SimplifiedStreamMixer.mix_streams(streams=streams, fluid_service=self.fluid_service)
