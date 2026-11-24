import abc
from collections.abc import Sequence

from libecalc.process.pump.liquid_stream import LiquidStream
from libecalc.process.pump.stream_distribution.liquid_stream_distribution import LiquidStreamDistribution


class HasLiquidValidity(abc.ABC):
    @abc.abstractmethod
    def is_valid(self, inlet_stream: LiquidStream) -> bool: ...


class LiquidPrioritiesStreamDistribution(LiquidStreamDistribution):
    """The first stream distribution under which every item is valid, else the last one.

    Stream ``i`` of a stream distribution belongs to ``items[i]``.
    """

    def __init__(self, stream_distributions: Sequence[LiquidStreamDistribution], items: Sequence[HasLiquidValidity]):
        if not stream_distributions:
            raise ValueError("At least one stream distribution is needed.")
        for index, stream_distribution in enumerate(stream_distributions):
            if stream_distribution.get_number_of_streams() != len(items):
                raise ValueError(
                    f"Stream distribution {index} has {stream_distribution.get_number_of_streams()} streams "
                    f"for {len(items)} items."
                )
        self._stream_distributions = tuple(stream_distributions)
        self._items = tuple(items)

    def get_number_of_streams(self) -> int:
        return len(self._items)

    def get_streams(self) -> list[LiquidStream]:
        _, streams = self.select()
        return streams

    def select(self) -> tuple[int, list[LiquidStream]]:
        """The index of the selected stream distribution and its streams."""
        *preferred, last = self._stream_distributions
        for index, stream_distribution in enumerate(preferred):
            streams = stream_distribution.get_streams()
            if all(item.is_valid(stream) for item, stream in zip(self._items, streams, strict=True)):
                return index, streams
        return len(preferred), last.get_streams()
