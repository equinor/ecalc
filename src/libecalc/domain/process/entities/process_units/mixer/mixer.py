from libecalc.domain.process.value_objects.fluid_stream import FluidStream, ProcessConditions, SimplifiedStreamMixing
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

        # Today for simplicity we assume that the first stream decides the pressure and temperature of all streams entering the mixer
        # This is how eCalc operates today. In the future we can implement more advanced mixing.
        new_streams = [streams[0]] + [
            stream.create_stream_with_new_conditions(
                conditions=ProcessConditions(
                    pressure_bara=streams[0].pressure_bara,
                    temperature_kelvin=streams[0].temperature_kelvin,
                ),
            )
            for stream in streams[1:]
        ]

        return self.mixing_strategy.mix_streams(streams=new_streams)
