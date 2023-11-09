from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List

import networkx as nx

from libecalc import dto
from libecalc.common.component_info.component_level import ComponentLevel
from libecalc.dto.base import ComponentType
from libecalc.dto.node_info import NodeInfo

if TYPE_CHECKING:
    from libecalc.dto.components import ComponentDTO

NodeID = str


class ComponentGraph:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.nodes: Dict[NodeID, ComponentDTO] = {}

    def add_node(self, node: ComponentDTO):
        self.graph.add_node(node.id)
        self.nodes[node.id] = node

    def add_edge(self, from_id: NodeID, to_id: NodeID):
        if from_id not in self.nodes or to_id not in self.nodes:
            raise ValueError("Add node before adding edges")

        self.graph.add_edge(from_id, to_id)

    def add_subgraph(self, subgraph: ComponentGraph):
        self.nodes.update(subgraph.nodes)
        self.graph = nx.compose(self.graph, subgraph.graph)

    def get_successors(self, node_id: NodeID, recursively=False) -> List[NodeID]:
        if recursively:
            return [
                successor_id
                for successor_id in nx.dfs_tree(self.graph, source=node_id).nodes()
                if successor_id != node_id
            ]
        else:
            return list(self.graph.successors(node_id))

    def get_predecessor(self, node_id: NodeID) -> NodeID:
        predecessors = list(self.graph.predecessors(node_id))
        if len(predecessors) > 1:
            raise ValueError("Component with several parents encountered.")
        return predecessors[0]

    def get_parent_installation_id(self, node_id: NodeID) -> NodeID:
        """
        Simple helper function to get the installation of any component with id

        Args:
            node_id:

        Returns:

        """

        # stop as soon as we get an installation. Ie. an installation of an installation, is itself...
        node_info = self.get_node_info(node_id)
        if node_info.component_level == ComponentLevel.INSTALLATION:
            return node_id

        parent_id = self.get_predecessor(node_id)
        return self.get_parent_installation_id(parent_id)

    @property
    def root(self) -> NodeID:
        return list(nx.topological_sort(self.graph))[0]

    def get_node_info(self, node_id: NodeID) -> NodeInfo:
        component_dto = self.nodes[node_id]
        if isinstance(component_dto, dto.Asset):
            component_level = ComponentLevel.ASSET
        elif isinstance(component_dto, dto.Installation):
            component_level = ComponentLevel.INSTALLATION
        elif isinstance(component_dto, dto.GeneratorSet):
            component_level = ComponentLevel.GENERATOR_SET
        elif component_dto.component_type in [
            ComponentType.COMPRESSOR_SYSTEM,
            ComponentType.PUMP_SYSTEM,
            ComponentType.CONSUMER_SYSTEM_V2,
        ]:
            component_level = ComponentLevel.SYSTEM
        else:
            component_level = ComponentLevel.CONSUMER

        return NodeInfo(
            id=component_dto.id,
            name=component_dto.name,
            component_type=component_dto.component_type,
            component_level=component_level,
        )

    def get_node(self, node_id: NodeID) -> ComponentDTO:
        return self.nodes[node_id]

    def get_node_id_by_name(self, name: str) -> NodeID:
        for node in self.nodes.values():
            if node.name == name:
                return node.id

        raise ValueError(f"Component with name '{name}' not found in '{self.nodes[self.root].name}'")

    def get_nodes_of_type(self, component_type: ComponentType) -> List[NodeID]:
        return [node.id for node in self.nodes.values() if node.component_type == component_type]

    @property
    def sorted_node_ids(self) -> List[NodeID]:
        return list(nx.topological_sort(self.graph))

    def __iter__(self):
        return iter(self.graph)
