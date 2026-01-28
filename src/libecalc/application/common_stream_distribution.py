import abc
from collections import defaultdict
from collections.abc import Hashable, Iterable
from dataclasses import dataclass
from typing import Generic, TypeVar

import networkx as nx
from libecalc.application.stream_distribution import StreamDistribution
from libecalc.domain.component_validation_error import DomainValidationException
from libecalc.domain.process.value_objects.fluid_stream import FluidService, FluidStream


class HasCapacity(abc.ABC):
    @abc.abstractmethod
    def get_unhandled_rate(self, rate: float, pressure: float) -> float: ...


T = TypeVar("T", bound=Hashable)


@dataclass
class Overflow(Generic[T]):
    from_id: T
    to_id: T


class CommonStreamDistribution(StreamDistribution, Generic[T]):
    def __init__(
        self,
        inlet_stream: FluidStream,
        items: dict[T, HasCapacity],
        rate_fractions: list[float],
        overflows: list[Overflow[T]],
        fluid_service: FluidService,
    ):
        self._items = items
        self._rates = [inlet_stream.standard_rate_sm3_per_day * rate_fraction for rate_fraction in rate_fractions]
        self._overflows = overflows
        self._inlet_stream = inlet_stream
        self._fluid_service = fluid_service
        self._overflow_graph: nx.DiGraph[T] = nx.DiGraph()
        for item_id in self._items.keys():
            self._overflow_graph.add_node(item_id)

        for overflow in self._overflows:
            self._overflow_graph.add_edge(overflow.from_id, overflow.to_id)

        if not nx.is_directed_acyclic_graph(self._overflow_graph):
            raise DomainValidationException("Overflow can not be cyclic")

    def get_number_of_streams(self) -> int:
        return len(self._rates)

    def _get_sorted_items(self) -> Iterable[T]:
        return nx.topological_sort(self._overflow_graph)

    def _get_overflow_out(self, item_id: T) -> Overflow[T] | None:
        for overflow in self._overflows:
            if overflow.from_id == item_id:
                return overflow
        return None

    def _adjust_for_overflow(self) -> dict[T, float]:
        overflow_map: dict[T, list[float]] = defaultdict(list)
        adjusted_rates: dict[T, float] = {}
        for item_id, rate in zip(self._get_sorted_items(), self._rates, strict=True):
            overflow = self._get_overflow_out(item_id)
            overflow_rate = sum(overflow_map[item_id])
            current_rate = rate + overflow_rate
            if overflow is not None:
                item = self._items[item_id]
                unhandled_rate = item.get_unhandled_rate(current_rate, self._inlet_stream.pressure_bara)
                handled_rate = current_rate - unhandled_rate
                overflow_map[overflow.to_id].append(unhandled_rate)
                adjusted_rates[item_id] = handled_rate
            else:
                adjusted_rates[item_id] = current_rate
        return adjusted_rates

    def get_streams(self) -> list[FluidStream]:
        rates = self._adjust_for_overflow()
        streams = {
            item_id: self._fluid_service.create_stream_from_standard_rate(
                fluid_model=self._inlet_stream.fluid_model,
                standard_rate_m3_per_day=rate,
                temperature_kelvin=self._inlet_stream.temperature_kelvin,
                pressure_bara=self._inlet_stream.pressure_bara,
            )
            for item_id, rate in rates.items()
        }
        return [streams[item_id] for item_id in self._items]
