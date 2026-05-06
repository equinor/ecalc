import uuid
from abc import ABC, abstractmethod
from typing import NewType

from libecalc.domain.energy.network.energy_stream import EnergyStream

EnergyNodeId = NewType("EnergyNodeId", uuid.UUID)


def create_energy_node_id() -> EnergyNodeId:
    return EnergyNodeId(uuid.uuid4())


class EnergyNode(ABC):
    """Base for anything in the energy network."""

    @abstractmethod
    def get_id(self) -> EnergyNodeId: ...


class Consumer(EnergyNode, ABC):
    """Knows its own demand — leaf node, entry point of the network."""

    @abstractmethod
    def get_demand(self) -> EnergyStream: ...


class Provider(EnergyNode, ABC):
    """Receives demand, transforms or fulfills it."""

    @abstractmethod
    def supply(self, demand: EnergyStream) -> EnergyStream: ...

    @abstractmethod
    def get_capacity_margin(self, demand: EnergyStream) -> float: ...
