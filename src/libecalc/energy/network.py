from collections.abc import Iterable
from graphlib import CycleError, TopologicalSorter
from typing import NewType, Self
from uuid import UUID

from libecalc.common.ddd import value_object
from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.energy.energy_unit import EnergyUnit, EnergyUnitId
from libecalc.energy.errors import InvalidEnergyNetworkError


@value_object
class EnergyConnection:
    """A directed connection between two energy nodes."""

    source_id: EnergyUnitId
    target_id: EnergyUnitId


EnergyNetworkId = NewType("EnergyNetworkId", UUID)


class EnergyNetwork:
    """A validated, directed acyclic graph of typed energy nodes."""

    def __init__(
        self,
        nodes: Iterable[EnergyUnit],
        connections: Iterable[EnergyConnection],
        energy_network_id: UUID | None = None,
    ):
        self._nodes: dict[
            EnergyUnitId,
            EnergyUnit,
        ] = {}

        for node in nodes:
            node_id = node.get_id()
            if node_id in self._nodes:
                raise InvalidEnergyNetworkError(f"Duplicate energy node ID: {node_id}")
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
        self._validate_required_predecessors()
        self._topological_order = self._create_topological_order()
        self._id = energy_network_id or EnergyNetwork._create_id()

    @classmethod
    def _create_id(cls: type[Self]) -> EnergyNetworkId:
        return EnergyNetworkId(ecalc_id_generator())

    def get_id(self) -> UUID:
        return self._id

    # Node access
    def get_node(
        self,
        node_id: EnergyUnitId,
    ) -> EnergyUnit:
        return self._nodes[node_id]

    def get_nodes(self) -> tuple[EnergyUnit, ...]:
        return tuple(self._nodes[node_id] for node_id in self._topological_order)

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

            self._successors[connection.source_id].add(connection.target_id)
            self._predecessors[connection.target_id].add(connection.source_id)

    def _validate_connection(
        self,
        connection: EnergyConnection,
    ) -> None:
        if connection.source_id not in self._nodes:
            raise InvalidEnergyNetworkError(f"Unknown source: {connection.source_id}")

        if connection.target_id not in self._nodes:
            raise InvalidEnergyNetworkError(f"Unknown target: {connection.target_id}")

        source = self._nodes[connection.source_id]
        target = self._nodes[connection.target_id]

        output_type = source.get_output_energy_type()
        if output_type is None:
            raise InvalidEnergyNetworkError(
                f"Connection source '{source.get_name()}' ({source.get_id()}) "
                f"of type {type(source).__name__} provides no output energy"
            )

        input_type = target.get_input_energy_type()
        if input_type is None:
            raise InvalidEnergyNetworkError(
                f"Connection target '{target.get_name()}' ({target.get_id()}) "
                f"of type {type(target).__name__} accepts no input energy"
            )
        if output_type is not input_type:
            raise InvalidEnergyNetworkError(
                f"Incompatible energy types for connection from "
                f"'{source.get_name()}' to "
                f"'{target.get_name()}': "
                f"source outputs {output_type.__name__}, "
                f"target accepts {input_type.__name__}"
            )

    def _validate_required_predecessors(self) -> None:
        for node_id, node in self._nodes.items():
            input_type = node.get_input_energy_type()

            if input_type is not None and not self._predecessors[node_id]:
                raise InvalidEnergyNetworkError(
                    f"Energy unit '{node.get_name()}' ({node_id}) requires input energy "
                    f"but has no predecessor; accepted input type: {input_type.__name__}"
                )

    def _create_topological_order(
        self,
    ) -> tuple[EnergyUnitId, ...]:
        try:
            return tuple(TopologicalSorter(self._predecessors).static_order())
        except CycleError as error:
            raise InvalidEnergyNetworkError("Energy network cannot be cyclic") from error
