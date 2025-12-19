from uuid import UUID

from libecalc.domain.process.entities.process_units.process_unit_type import ProcessUnitType
from libecalc.domain.process.process_system import ProcessEntityID, ProcessUnit
from libecalc.domain.process.value_objects.fluid_stream import FluidStream, SimplifiedStreamMixing
from libecalc.domain.process.value_objects.fluid_stream.mixing import StreamMixingStrategy


class Mixer(ProcessUnit):
    def __init__(self, number_of_inputs: int, unit_id: ProcessEntityID, mixing_strategy: StreamMixingStrategy = None):
        self.number_of_inputs = number_of_inputs
        self._unit_id = unit_id
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

    def get_id(self) -> UUID:
        return self._unit_id

    def get_type(self) -> str:
        return ProcessUnitType.MIXER.value
