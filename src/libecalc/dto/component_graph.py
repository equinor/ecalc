from __future__ import annotations

from typing import List

from libecalc.common.component_info.component_level import ComponentLevel
from libecalc.common.component_type import ComponentType
from libecalc.common.graph import Graph, NodeID
from libecalc.dto.node_info import NodeInfo


class ComponentGraph(Graph):
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

    def get_node_info(self, node_id: NodeID) -> NodeInfo:
        component_dto = self.nodes[node_id]
        if component_dto.component_type == ComponentType.ASSET:
            component_level = ComponentLevel.ASSET
        elif component_dto.component_type == ComponentType.INSTALLATION:
            component_level = ComponentLevel.INSTALLATION
        elif component_dto.component_type == ComponentType.GENERATOR_SET:
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

    def get_node_id_by_name(self, name: str) -> NodeID:
        for node in self.nodes.values():
            if node.name == name:
                return node.id

        raise ValueError(f"Component with name '{name}' not found in '{self.nodes[self.root].name}'")

    def get_nodes_of_type(self, component_type: ComponentType) -> List[NodeID]:
        return [node.id for node in self.nodes.values() if node.component_type == component_type]
