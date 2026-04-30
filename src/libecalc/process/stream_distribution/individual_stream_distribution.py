from collections.abc import Sequence

from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.stream_distribution.stream_distribution import StreamDistribution


class IndividualStreamDistribution(StreamDistribution):
    def __init__(self, streams: Sequence[FluidStream]):
        self._streams = streams

    def get_number_of_streams(self) -> int:
        return len(self._streams)

    def get_streams(self) -> list[FluidStream]:
        return list(self._streams)
