from collections.abc import Sequence

from libecalc.domain.process.stream_distribution.stream_distribution import StreamDistribution
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class IndividualStreamDistribution(StreamDistribution):
    def __init__(self, streams: Sequence[FluidStream]):
        self._streams = streams

    def get_number_of_streams(self) -> int:
        return len(self._streams)

    def get_streams(self) -> list[FluidStream]:
        return list(self._streams)
