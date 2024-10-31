from __future__ import annotations

from typing import Generic, Protocol, Self, TypeVar

import networkx as nx

NodeID = str


class NodeWithID(Protocol):
    @property
    def id(self) -> NodeID: ...


TNode = TypeVar("TNode", bound=NodeWithID)


class Graph(Generic[TNode]):
    def __init__(self):
        self.graph = nx.DiGraph()
        self.nodes: dict[NodeID, TNode] = {}

    def add_node(self, node: TNode) -> Self:
        self.graph.add_node(node.id)
        self.nodes[node.id] = node
        return self

    def add_edge(self, from_id: NodeID, to_id: NodeID) -> Self:
        if from_id not in self.nodes or to_id not in self.nodes:
            raise ValueError("Add node before adding edges")

        self.graph.add_edge(from_id, to_id)
        return self

    def add_subgraph(self, subgraph: Graph) -> Self:
        self.nodes.update(subgraph.nodes)
        self.graph = nx.compose(self.graph, subgraph.graph)
        return self

    def get_successors(self, node_id: NodeID, recursively=False) -> list[NodeID]:
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
            raise ValueError(
                f"Tried to get a single predecessor of node with several predecessors. NodeID: {node_id}, "
                f"Predecessors: {', '.join(predecessors)}"
            )
        return predecessors[0]

    @property
    def root(self) -> NodeID:
        return list(nx.topological_sort(self.graph))[0]

    def get_node(self, node_id: NodeID) -> TNode:
        return self.nodes[node_id]

    @property
    def sorted_node_ids(self) -> list[NodeID]:
        return list(nx.topological_sort(self.graph))

    def breadth_first_search_tree(self, source_id: NodeID) -> list[NodeID]:
        """
        Create a tree with source as root by searching edges close to the source first. Breadth first orders the nodes
        that are closer to the source before nodes that are further out.

        Args:
            source_id:

        Returns:

        """
        return list(nx.bfs_tree(self.graph, source_id))

    def __iter__(self):
        return iter(self.graph)
