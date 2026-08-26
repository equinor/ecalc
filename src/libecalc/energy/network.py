from collections.abc import Iterable
from graphlib import CycleError, TopologicalSorter

from libecalc.common.ddd import value_object
from libecalc.energy.consumer import Consumer
from libecalc.energy.demand import Demand
from libecalc.energy.energy_unit import EnergyUnitId
from libecalc.energy.energy_units import Junction
from libecalc.energy.errors import InvalidEnergyNetworkError
from libecalc.energy.provider import Converter, Provider

type EnergyNetworkNode = Consumer[Demand] | Provider[Demand] | Junction[Demand]


@value_object
class EnergyConnection:
    """A directed connection between two energy units."""

    source_id: EnergyUnitId
    target_id: EnergyUnitId


class EnergyNetwork:
    """A validated, directed acyclic graph of typed energy units."""

    def __init__(
        self,
        nodes: Iterable[EnergyNetworkNode],
        connections: Iterable[EnergyConnection],
    ):
        self._nodes: dict[
            EnergyUnitId,
            EnergyNetworkNode,
        ] = {}

        for node in nodes:
            node_id = node.get_id()
            if node_id in self._nodes:
                raise ValueError(f"Duplicate energy node ID: {node_id}")
            self._nodes[node_id] = node

        self._predecessors: dict[
            EnergyUnitId,
            set[EnergyUnitId],
        ] = {node_id: set() for node_id in self._nodes}
        self._successors: dict[
            EnergyUnitId,
            set[EnergyUnitId],
        ] = {node_id: set() for node_id in self._nodes}

        self._add_connections(connections)
        self._topological_order = self._create_topological_order()

    def get_node(
        self,
        node_id: EnergyUnitId,
    ) -> EnergyNetworkNode:
        return self._nodes[node_id]

    def predecessors(
        self,
        node_id: EnergyUnitId,
    ) -> frozenset[EnergyUnitId]:
        return frozenset(self._predecessors[node_id])

    def successors(
        self,
        node_id: EnergyUnitId,
    ) -> frozenset[EnergyUnitId]:
        return frozenset(self._successors[node_id])

    def topological_order(
        self,
    ) -> tuple[EnergyUnitId, ...]:
        return self._topological_order

    def _add_connections(
        self,
        connections: Iterable[EnergyConnection],
    ) -> None:
        for connection in connections:
            self._validate_connection(connection)

            self._successors[connection.source_id].add(connection.target_id)
            self._predecessors[connection.target_id].add(connection.source_id)

    def _validate_connection(
        self,
        connection: EnergyConnection,
    ) -> None:
        if connection.source_id not in self._nodes:
            raise ValueError(f"Unknown source: {connection.source_id}")

        if connection.target_id not in self._nodes:
            raise ValueError(f"Unknown target: {connection.target_id}")

        source = self._nodes[connection.source_id]
        target = self._nodes[connection.target_id]

        provided_demand_type = self._get_provided_demand_type(source)
        required_demand_type = self._get_required_demand_type(target)

        if provided_demand_type is not required_demand_type:
            raise ValueError(
                f"Incompatible demand types: {provided_demand_type.__name__} -> {required_demand_type.__name__}"
            )

    @staticmethod
    def _get_provided_demand_type(
        node: EnergyNetworkNode,
    ) -> type[Demand]:
        if isinstance(node, Provider):
            return node.provided_demand_type

        if isinstance(node, Junction):
            return node.demand_type

        raise ValueError("Source node provides no energy")

    @staticmethod
    def _get_required_demand_type(
        node: EnergyNetworkNode,
    ) -> type[Demand]:
        if isinstance(node, Consumer):
            return node.required_demand_type

        if isinstance(node, Converter):
            return node.required_demand_type

        if isinstance(node, Junction):
            return node.demand_type

        raise ValueError("Target node requires no energy")

    def _create_topological_order(
        self,
    ) -> tuple[EnergyUnitId, ...]:
        try:
            return tuple(TopologicalSorter(self._predecessors).static_order())
        except CycleError as error:
            raise InvalidEnergyNetworkError("Energy network cannot be cyclic") from error
