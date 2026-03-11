from libecalc.domain.process.entities.process_units.simplified_stream_mixer.simplified_stream_mixer import (
    SimplifiedStreamMixer,
)
from libecalc.domain.process.process_system.process_unit import ProcessUnit, ProcessUnitId
from libecalc.domain.process.value_objects.fluid_stream import FluidService, FluidStream


class Mixer(ProcessUnit):
    def __init__(
        self,
        process_unit_id: ProcessUnitId,
        number_of_inputs: int,
        fluid_service: FluidService,
    ):
        self._id = process_unit_id
        self.number_of_inputs = number_of_inputs  # TODO: We should probably add some validation somewhere to ensure that the number of inputs is at least 2, as a mixer with only one input does not make sense.
        self._stream_mixer = SimplifiedStreamMixer(fluid_service)

        # Empty list at initialization, as we do not know the additional streams at this point.
        # The additional streams will be set later using the set_additional_streams method.
        self._additional_streams: list[FluidStream] = []

    def set_additional_streams(self, streams: list[FluidStream]):
        """
        Stores additional streams to the mixer. This is used to store any additional streams that are
        not part of the main inlet stream, but are still needed for the mixing process.
        For example, if we have a mixer with 2 inlets, and we only have one inlet streams, we can
        store the other stream here until it is needed for the mixing process.

        Args:
            streams (list[FluidStream]): The additional streams to be mixed with the main inlet_stream.
        """
        self._additional_streams = streams

    def get_id(self) -> ProcessUnitId:
        return self._id

    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream:
        """
        Mixes multiple fluid streams into a single stream.

        Additional streams matching the number of inputs defined for the mixer needs to be
        defined prior to calling this method, otherwise the method will raise an error.

        Args:
            inlet_stream (FluidStream): The main inlet stream.

        Returns:
            FluidStream: The resulting mixed fluid stream.
        """
        # check that the additional stream is not empty, if it is, we cannot propagate the stream
        if len(self._additional_streams) == 0:
            raise ValueError("No additional stream provided for the mixer. Cannot propagate the stream.")
        # we can only propagate the stream if we have the correct number of additional streams
        if len(self._additional_streams) != self.number_of_inputs - 1:
            raise ValueError(
                "Number of additional streams does not match the number of inputs defined for the mixer. Cannot propagate the stream."
            )

        streams = [inlet_stream] + self._additional_streams

        if sum(s.mass_rate_kg_per_h for s in streams) == 0:
            # when all streams have zero mass rate, we can just return the inlet stream, as the result will be the same regardless of the mixing method used (as there is no mass to mix).
            return inlet_stream

        return self._stream_mixer.mix_streams(streams=streams)
