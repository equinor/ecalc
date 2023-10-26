from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List

import networkx as nx
from libecalc import dto
from libecalc.common.component_info.component_level import ComponentLevel
from libecalc.dto.base import ComponentType
from libecalc.dto.node_info import NodeInfo

if TYPE_CHECKING:
    from libecalc.dto.components import ComponentDTO


class Graph:
    def __init__(self):
        self.graph = nx.DiGraph()
        self.components: Dict[str, ComponentDTO] = {}

    def add_node(self, component: ComponentDTO):
        self.graph.add_node(component.id)
        self.components[component.id] = component

    def add_edge(self, from_id: str, to_id: str):
        if from_id not in self.components or to_id not in self.components:
            raise ValueError("Add node before adding edges")

        self.graph.add_edge(from_id, to_id)

    def add_subgraph(self, subgraph: Graph):
        self.components.update(subgraph.components)
        self.graph = nx.compose(self.graph, subgraph.graph)

    def get_successors(self, component_id: str, recursively=False) -> List[str]:
        if recursively:
            return [
                successor_id
                for successor_id in nx.dfs_tree(self.graph, source=component_id).nodes()
                if successor_id != component_id
            ]
        else:
            return self.graph.successors(component_id)

    def get_predecessor(self, component_id: str) -> str:
        predecessors = list(self.graph.predecessors(component_id))
        if len(predecessors) > 1:
            raise ValueError("Component with several parents encountered.")
        return predecessors[0]

    def get_parent_installation_id(self, component_id: str) -> str:
        """
        Simple helper function to get the installation of any component with id

        Args:
            component_id:

        Returns:

        """

        # stop as soon as we get an installation. Ie. an installation of an installation, is itself...
        node_info = self.get_node_info(component_id)
        if node_info.component_level == ComponentLevel.INSTALLATION:
            return component_id

        parent_id = self.get_predecessor(component_id)
        return self.get_parent_installation_id(parent_id)

    @property
    def root(self) -> str:
        return list(nx.topological_sort(self.graph))[0]

    def get_node_info(self, component_id: str) -> NodeInfo:
        component_dto = self.components[component_id]
        if isinstance(component_dto, dto.Asset):
            component_level = ComponentLevel.ASSET
        elif isinstance(component_dto, dto.Installation):
            component_level = ComponentLevel.INSTALLATION
        elif isinstance(component_dto, dto.GeneratorSet):
            component_level = ComponentLevel.GENERATOR_SET
        elif component_dto.component_type in [
            ComponentType.COMPRESSOR_SYSTEM_V2,
            ComponentType.COMPRESSOR_SYSTEM,
            ComponentType.PUMP_SYSTEM,
            ComponentType.PUMP_SYSTEM_V2,
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

    def get_component(self, component_id: str) -> ComponentDTO:
        return self.components[component_id]

    def get_component_id_by_name(self, name: str) -> str:
        for component in self.components.values():
            if component.name == name:
                return component.id

        raise ValueError(f"Component with name '{name}' not found in '{self.components[self.root].name}'")

    def get_nodes(self, component_type: ComponentType) -> List[str]:
        return [node.id for node in self.components.values() if node.component_type == component_type]

    @property
    def sorted_component_ids(self) -> List[str]:
        return list(nx.topological_sort(self.graph))

    def __iter__(self):
        return iter(self.graph)
