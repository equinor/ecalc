from collections.abc import Iterable, Sequence
from graphlib import CycleError, TopologicalSorter
from typing import NewType, Self
from uuid import UUID

from libecalc.common.ddd import value_object
from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.energy.energy_types import Energy
from libecalc.energy.energy_unit import EnergyUnitId
from libecalc.energy.errors import InvalidEnergyNetworkError

EnergyNetworkId = NewType("EnergyNetworkId", UUID)
EnergyConnectionId = NewType("EnergyConnectionId", UUID)


@value_object
class EnergyConnection:
    """A directed connection between two energy nodes."""

    id: EnergyConnectionId
    source_id: EnergyUnitId
    target_id: EnergyUnitId
    energy_type: type[Energy]


class EnergyNetwork:
    """A validated, directed acyclic graph of energy connections."""

    def __init__(
        self,
        nodes: Sequence[EnergyUnitId],
        connections: Iterable[EnergyConnection],
        energy_network_id: UUID | None = None,
    ):
        self._nodes: list[EnergyUnitId] = []

        for node_id in nodes:
            if node_id in self._nodes:
                raise InvalidEnergyNetworkError(f"Duplicate energy node ID: {node_id}")
            self._nodes.append(node_id)

        self._predecessors: dict[
            EnergyUnitId,
            set[EnergyUnitId],
        ] = {node_id: set() for node_id in self._nodes}
        self._successors: dict[
            EnergyUnitId,
            set[EnergyUnitId],
        ] = {node_id: set() for node_id in self._nodes}

        self._connections: dict[tuple[EnergyUnitId, EnergyUnitId], EnergyConnection] = {}
        self._connections_by_id: dict[EnergyConnectionId, EnergyConnection] = {}
        self._add_connections(connections)
        self._topological_order = self._create_topological_order()
        self._id = energy_network_id or EnergyNetwork._create_id()

    @classmethod
    def _create_id(cls: type[Self]) -> EnergyNetworkId:
        return EnergyNetworkId(ecalc_id_generator())

    @classmethod
    def create(
        cls,
        node_input_types: dict[EnergyUnitId, type[Energy] | None],
        node_output_types: dict[EnergyUnitId, type[Energy] | None],
        connections: Iterable[tuple[EnergyUnitId, EnergyUnitId]],
        energy_network_id: UUID | None = None,
    ) -> Self:
        """Create a network after deriving and validating each connection's energy type."""
        if node_input_types.keys() != node_output_types.keys():
            raise InvalidEnergyNetworkError("Node input and output types must be provided for the same node IDs")

        connection_list: list[EnergyConnection] = []
        predecessors = {node_id: set() for node_id in node_input_types}
        for source_id, target_id in connections:
            if source_id not in node_input_types:
                raise InvalidEnergyNetworkError(f"Unknown source: {source_id}")
            if target_id not in node_input_types:
                raise InvalidEnergyNetworkError(f"Unknown target: {target_id}")

            output_type = node_output_types[source_id]
            input_type = node_input_types[target_id]
            if output_type is None:
                raise InvalidEnergyNetworkError(f"Connection source {source_id} provides no output energy")
            if input_type is None:
                raise InvalidEnergyNetworkError(f"Connection target {target_id} accepts no input energy")
            if output_type is not input_type:
                raise InvalidEnergyNetworkError(
                    f"Incompatible energy types for connection from {source_id} to {target_id}: "
                    f"source outputs {output_type.__name__}, target accepts {input_type.__name__}"
                )
            predecessors[target_id].add(source_id)
            connection_list.append(
                EnergyConnection(
                    id=EnergyConnectionId(ecalc_id_generator()),
                    source_id=source_id,
                    target_id=target_id,
                    energy_type=output_type,
                )
            )

        for node_id, input_type in node_input_types.items():
            if input_type is not None and not predecessors[node_id]:
                raise InvalidEnergyNetworkError(
                    f"Energy unit {node_id} requires input energy but has no predecessor; "
                    f"accepted input type: {input_type.__name__}"
                )

        return cls(
            nodes=list(node_input_types.keys()), connections=connection_list, energy_network_id=energy_network_id
        )

    def get_id(self) -> UUID:
        return self._id

    def get_nodes(self) -> Sequence[EnergyUnitId]:
        return tuple(self._nodes)

    def get_connections(self) -> tuple[EnergyConnection, ...]:
        return tuple(self._connections.values())

    def get_connection(self, source_id: EnergyUnitId, target_id: EnergyUnitId) -> EnergyConnection:
        return self._connections[source_id, target_id]

    def get_connection_by_id(self, connection_id: EnergyConnectionId) -> EnergyConnection:
        return self._connections_by_id[connection_id]

    # Topology
    def get_predecessors(
        self,
        node_id: EnergyUnitId,
    ) -> frozenset[EnergyUnitId]:
        return frozenset(self._predecessors[node_id])

    def get_successors(
        self,
        node_id: EnergyUnitId,
    ) -> frozenset[EnergyUnitId]:
        return frozenset(self._successors[node_id])

    def get_topological_order(
        self,
    ) -> tuple[EnergyUnitId, ...]:
        return self._topological_order

    # Private topology construction and validation
    def _add_connections(
        self,
        connections: Iterable[EnergyConnection],
    ) -> None:
        for connection in connections:
            self._validate_connection(connection)

            if connection.id in self._connections_by_id:
                raise InvalidEnergyNetworkError(f"Duplicate energy connection ID: {connection.id}")
            if (connection.source_id, connection.target_id) in self._connections:
                raise InvalidEnergyNetworkError(
                    f"Duplicate energy connection from {connection.source_id} to {connection.target_id}"
                )

            self._successors[connection.source_id].add(connection.target_id)
            self._predecessors[connection.target_id].add(connection.source_id)
            self._connections[connection.source_id, connection.target_id] = connection
            self._connections_by_id[connection.id] = connection

    def _validate_connection(
        self,
        connection: EnergyConnection,
    ) -> None:
        if connection.source_id not in self._nodes:
            raise InvalidEnergyNetworkError(f"Unknown source: {connection.source_id}")

        if connection.target_id not in self._nodes:
            raise InvalidEnergyNetworkError(f"Unknown target: {connection.target_id}")

    def _create_topological_order(
        self,
    ) -> tuple[EnergyUnitId, ...]:
        try:
            return tuple(TopologicalSorter(self._predecessors).static_order())
        except CycleError as error:
            raise InvalidEnergyNetworkError("Energy network cannot be cyclic") from error
