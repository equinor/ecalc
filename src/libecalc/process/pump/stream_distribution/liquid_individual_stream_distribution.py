from collections.abc import Sequence

from libecalc.process.pump.liquid_stream import LiquidStream
from libecalc.process.pump.stream_distribution.liquid_stream_distribution import LiquidStreamDistribution


class LiquidIndividualStreamDistribution(LiquidStreamDistribution):
    """One inlet stream per pump."""

    def __init__(self, streams: Sequence[LiquidStream]):
        self._streams = tuple(streams)

    def get_number_of_streams(self) -> int:
        return len(self._streams)

    def get_streams(self) -> list[LiquidStream]:
        return list(self._streams)
