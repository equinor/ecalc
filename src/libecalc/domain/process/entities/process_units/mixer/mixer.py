from libecalc.domain.process.value_objects.fluid_stream import FluidStream, SimplifiedStreamMixing
from libecalc.domain.process.value_objects.fluid_stream.mixing import StreamMixingStrategy


class Mixer:
    def __init__(self, number_of_inputs: int, mixing_strategy: StreamMixingStrategy = None):
        self.number_of_inputs = number_of_inputs
        self.mixing_strategy = mixing_strategy or SimplifiedStreamMixing()

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

        return self.mixing_strategy.mix_streams(streams=streams)
