import abc

from libecalc.application.stream_distribution import StreamDistribution
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


class HasValidity(abc.ABC):
    @abc.abstractmethod
    def is_valid(self, inlet_stream: FluidStream) -> bool: ...


def find_first_valid(stream_distributions: list[StreamDistribution], items: list[HasValidity]) -> list[FluidStream]:
    assert len(stream_distributions) > 0
    for stream_distribution in stream_distributions:
        streams = stream_distribution.get_streams()
        if all(item.is_valid(stream) for item, stream in zip(items, stream_distribution.get_streams(), strict=True)):
            return streams

    return streams


class PrioritiesStreamDistribution(StreamDistribution):
    def __init__(self, stream_distributions: list[StreamDistribution], items: list[HasValidity]):
        self._stream_distributions = stream_distributions
        self._items = items

    def get_number_of_streams(self) -> int:
        return len(self._items)

    def get_streams(self) -> list[FluidStream]:
        return find_first_valid(self._stream_distributions, self._items)
