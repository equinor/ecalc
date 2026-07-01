from abc import ABC, abstractmethod
from dataclasses import dataclass

from libecalc.domain.energy.network.energy_node import (
    Consumer,
    EnergyNode,
    EnergyNodeId,
    Provider,
    create_energy_node_id,
)
from libecalc.domain.energy.network.energy_stream import EnergyStream, EnergyType


@dataclass(frozen=True)
class EnergyChainResult:
    """Complete result from running an energy chain."""

    demand: EnergyStream  # mechanical demand from consumer
    fuel: EnergyStream  # fuel consumption from supply chain
    capacity_margin_mw: float  # tightest margin across all providers


class EnergySystem(Provider, ABC):
    """A composite provider that contains other energy nodes."""

    @abstractmethod
    def get_children(self) -> list[EnergyNode]: ...


@dataclass
class EnergyChain:
    """A consumer connected to its supply chain."""

    consumer: Consumer
    supply_chain: EnergySystem

    def run(self) -> EnergyChainResult:
        """Run the full energy chain: demand → supply → fuel + margin."""
        demand = self.consumer.get_demand()
        fuel = self.supply_chain.supply(demand)
        capacity_margin = self.supply_chain.get_capacity_margin(demand)
        return EnergyChainResult(
            demand=demand,
            fuel=fuel,
            capacity_margin_mw=capacity_margin,
        )

    def get_all_nodes(self) -> list[EnergyNode]:
        """Full graph including demand side."""
        return [self.consumer, *self.supply_chain.get_children()]


class PowerBus(EnergySystem):
    """
    Distributes electrical demand across multiple sources by priority.

    Sources are tried in order. If a source cannot fully meet the remaining
    demand (indicated by get_capacity_margin), it delivers what it can and the
    remainder spills to the next source.
    """

    def __init__(self, sources: list[Provider]):
        self._id = create_energy_node_id()
        self._sources = sources

    def get_id(self) -> EnergyNodeId:
        return self._id

    def get_children(self) -> list[EnergyNode]:
        return list(self._sources)

    def supply(self, demand: EnergyStream) -> EnergyStream:
        if demand.energy_type != EnergyType.ELECTRICAL:
            raise ValueError(f"Power bus expects electrical demand, got {demand.energy_type}")

        remaining = demand.value
        total_fuel = 0.0

        for source in self._sources:
            if remaining <= 0:
                break

            margin = source.get_capacity_margin(EnergyStream.electrical(remaining))
            if margin < 0:
                # Source can only partially cover remaining demand.
                deliverable = max(0.0, remaining + margin)
                result = source.supply(EnergyStream.electrical(deliverable))
                total_fuel += result.value
                remaining -= deliverable
                continue

            # Source can cover all remaining demand.
            result = source.supply(EnergyStream.electrical(remaining))
            total_fuel += result.value
            remaining = 0.0

        return EnergyStream.fuel(total_fuel)

    def get_capacity_margin(self, demand: EnergyStream) -> float:
        """Total spare capacity across all sources."""
        total_margin = 0.0
        for source in self._sources:
            total_margin += max(0.0, source.get_capacity_margin(demand))
        return total_margin - demand.value


class SerialEnergySystem(EnergySystem):
    """
    Chain of providers where each node transforms demand and passes it to the next.

    Demand enters the first node. If the node outputs a non-fuel stream (e.g. electrical),
    that becomes the demand for the next node. When a node outputs fuel, the chain terminates.
    """

    def __init__(self, nodes: list[Provider]):
        self._id = create_energy_node_id()
        self._nodes = nodes

    def get_id(self) -> EnergyNodeId:
        return self._id

    def get_children(self) -> list[EnergyNode]:
        return list(self._nodes)

    def supply(self, demand: EnergyStream) -> EnergyStream:
        """Propagate demand through each node until fuel is reached."""
        current = demand
        for node in self._nodes:
            current = node.supply(current)
            if current.energy_type == EnergyType.FUEL:
                return current
        return current

    def get_capacity_margin(self, demand: EnergyStream) -> float:
        """Tightest margin across all nodes in the chain."""
        min_margin = float("inf")
        current = demand
        for node in self._nodes:
            margin = node.get_capacity_margin(current)
            min_margin = min(min_margin, margin)
            current = node.supply(current)
            if current.energy_type == EnergyType.FUEL:
                break
        return min_margin
