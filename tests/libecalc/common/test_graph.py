from dataclasses import dataclass
from typing import Optional

import pytest

from libecalc.common.graph import Graph, NodeID


@dataclass
class Node:
    node_id: NodeID
    some_data: Optional[str] = None

    @property
    def id(self):
        return self.node_id


@pytest.fixture
def graph_with_subgraph():
    subgraph = (
        Graph()
        .add_node(Node(node_id="3"))
        .add_node(Node(node_id="4", some_data="test"))
        .add_edge(from_id="3", to_id="4")
    )

    graph = (
        Graph()
        .add_subgraph(subgraph)
        .add_node(Node(node_id="2"))
        .add_node(Node(node_id="1"))
        .add_edge(from_id="1", to_id="2")
        .add_edge("2", "3")
    )

    return graph


class TestGraph:
    def test_get_successors(self):
        graph = (
            Graph()
            .add_node(Node(node_id="1"))
            .add_node(Node(node_id="2"))
            .add_node(Node(node_id="3"))
            .add_edge(from_id="1", to_id="2")
            .add_edge(from_id="2", to_id="3")
        )
        assert graph.get_successors("1") == ["2"]
        assert graph.get_successors("1", recursively=True) == ["2", "3"]
        assert graph.get_successors("2", recursively=True) == ["3"]
        assert graph.get_successors("3", recursively=True) == []

    def test_get_predecessors(self):
        graph = (
            Graph()
            .add_node(Node(node_id="1"))
            .add_node(Node(node_id="2"))
            .add_node(Node(node_id="3"))
            .add_edge(from_id="1", to_id="2")
            .add_edge(from_id="2", to_id="3")
        )

        assert graph.get_predecessor("3") == "2"
        assert graph.get_predecessor("2") == "1"

        graph.add_edge("1", "3")
        with pytest.raises(ValueError) as exc_info:
            graph.get_predecessor("3")

        assert str(exc_info.value) == (
            "Tried to get a single predecessor of node with several predecessors. NodeID: " "3, Predecessors: 2, 1"
        )

    def test_subgraph(self, graph_with_subgraph):
        assert len(graph_with_subgraph.nodes) == 4
        assert set(graph_with_subgraph.nodes.keys()) == {"1", "2", "3", "4"}
        assert graph_with_subgraph.get_predecessor("3") == "2"

    def test_topological_sort(self, graph_with_subgraph):
        assert graph_with_subgraph.sorted_node_ids == ["1", "2", "3", "4"]

    def test_root(self, graph_with_subgraph):
        assert graph_with_subgraph.root == "1"

    def test_get_node_with_data(self, graph_with_subgraph):
        """
        Assert returned node is the same node that we passed in.

        Args:
            graph_with_subgraph:

        Returns:

        """
        node = graph_with_subgraph.get_node("4")
        #  TODO: fix typing
        #   Uncomment line below to see the type, no import needed, install mypy in poetry venv, run poetry shell, then
        #    run mypy on the file 'mypy <path to file>'.
        # reveal_type(node)
        assert isinstance(node, Node)
        assert node.some_data == "test"
