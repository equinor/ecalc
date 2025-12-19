from collections.abc import Sequence

from libecalc.common.graph import Graph
from libecalc.domain.energy import EnergyComponent, EnergyContainerID, EnergyModel


class EnergyContainerEnergyModel(EnergyModel):
    def __init__(self, graph: Graph[EnergyContainerID], nodes: dict[EnergyContainerID, EnergyComponent]):
        self._graph = graph
        self._nodes = nodes

    def get_energy_container(self, container_id: EnergyContainerID) -> EnergyComponent:
        return self._nodes[container_id]

    def get_energy_containers(self) -> Sequence[EnergyContainerID]:
        return self._graph.graph.nodes

    def get_energy_components(self) -> Sequence[EnergyContainerID]:
        return self.get_energy_containers()

    def get_children(self, container_id: EnergyContainerID) -> list[EnergyContainerID]:
        return self._graph.get_successors(container_id)

    def get_consumers(self, provider_id: EnergyContainerID) -> list[EnergyContainerID]:
        return self.get_children(provider_id)

    def get_all_children(self, container_id: EnergyContainerID) -> list[EnergyContainerID]:
        return self._graph.get_successors(container_id, recursively=True)

    def get_parent(self, container_id: EnergyContainerID) -> EnergyContainerID:
        return self._graph.get_predecessor(container_id)

    def get_root(self) -> EnergyContainerID:
        return self._graph.root


class EnergyContainerEnergyModelBuilder:
    def __init__(self):
        self._nodes: dict[EnergyContainerID, EnergyComponent] = {}
        self._edges: list[tuple[EnergyContainerID, EnergyContainerID]] = []

    def register_energy_container(
        self, container_id: EnergyContainerID, parent_id: EnergyContainerID | None, energy_container: EnergyComponent
    ):
        self._nodes[container_id] = energy_container
        if parent_id:
            self._edges.append((parent_id, container_id))

    def build(self) -> EnergyModel:
        graph: Graph[EnergyContainerID] = Graph()
        for node_id in self._nodes:
            graph.add_node(node_id)

        for from_id, to_id in self._edges:
            graph.add_edge(from_id, to_id)

        return EnergyContainerEnergyModel(
            graph=graph,
            nodes=self._nodes,
        )
