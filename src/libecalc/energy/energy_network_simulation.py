import abc
import operator
from collections.abc import Iterable, Mapping, Sequence
from functools import reduce
from typing import Any

from libecalc.energy import Energy, EnergyUnit, EnergyUnitId
from libecalc.energy.energy_network import EnergyNetwork
from libecalc.energy.energy_network_topology import EnergyConnection, EnergyConnectionId, EnergyNetworkTopology
from libecalc.energy.errors import InvalidEnergyNetworkInputError


class EnergyUnitFactory(abc.ABC):
    """Owns node configuration and creates units for individual operating points."""

    @abc.abstractmethod
    def get_id(self) -> EnergyUnitId: ...

    @abc.abstractmethod
    def get_name(self) -> str: ...

    @abc.abstractmethod
    def create(
        self,
        demand: Energy,
        *,
        incoming_connections: Sequence[EnergyConnection],
        **extra: Any,
    ) -> EnergyUnit:
        """Create a unit for the required output `demand`, using context such as the period from `extra`."""
        ...


class EnergyNetworkSimulation:
    def __init__(
        self,
        topology: EnergyNetworkTopology,
        energy_unit_factories: Iterable[EnergyUnitFactory],
    ) -> None:
        self._topology = topology
        self._energy_unit_factories: dict[EnergyUnitId, EnergyUnitFactory] = {}

        for energy_unit_factory in energy_unit_factories:
            energy_unit_id = energy_unit_factory.get_id()
            assert energy_unit_id not in self._energy_unit_factories, "Duplicate energy unit factory"
            self._energy_unit_factories[energy_unit_id] = energy_unit_factory

        assert self._energy_unit_factories.keys() <= set(self._topology.get_nodes())
        exclusive_input_nodes = self._topology.get_exclusive_input_nodes()
        for node_id in self._topology.get_nodes():
            if node_id not in self._energy_unit_factories:
                assert not self._topology.get_successors(node_id), "Missing factory for a supplying node"
                is_exclusive = node_id in exclusive_input_nodes
                assert is_exclusive or len(self._topology.get_predecessors(node_id)) <= 1, (
                    "A consumer cannot split its demand"
                )

    def run(
        self,
        connection_demands: dict[EnergyConnectionId, Energy],
        active_connections: Mapping[EnergyUnitId, EnergyUnitId] | None = None,
        **extra: Any,
    ) -> EnergyNetwork:
        """Calculate connection energies and capacity failures from demands on consumer-targeting connections.

        `extra` is forwarded to every factory, for example to select the evaluation period. `active_connections`
        must have exactly one entry per exclusive-input node, naming which predecessor is active.
        """
        active_connections = active_connections or {}
        self._validate_active_connections(active_connections)
        self._validate_connection_demands(connection_demands, active_connections)

        energy_units: dict[EnergyUnitId, EnergyUnit] = {}
        connection_energy: dict[EnergyConnectionId, Energy] = dict(connection_demands)
        self._zero_inactive_candidates(active_connections, connection_energy)

        for node_id in reversed(self._topology.get_topological_order()):
            outgoing_connections = self._topology.get_outgoing_connections(node_id)
            if not outgoing_connections:
                # Leaf consumers have no outgoing energy to propagate upstream.
                continue

            demand = reduce(operator.add, [connection_energy[connection.id] for connection in outgoing_connections])
            incoming_connections = self._incoming_connections_for(node_id, active_connections)

            energy_unit = self._energy_unit_factories[node_id].create(
                demand,
                incoming_connections=incoming_connections,
                **extra,
            )
            input_energies = energy_unit.get_input_energies()
            # An extra key would silently overwrite another node's connection energy.
            assert input_energies.keys() == {connection.id for connection in incoming_connections}

            energy_units[node_id] = energy_unit
            connection_energy.update(input_energies)

        return EnergyNetwork(
            topology=self._topology,
            energy_units=energy_units,
            connection_energy=connection_energy,
        )

    def _incoming_connections_for(
        self, node_id: EnergyUnitId, active_connections: Mapping[EnergyUnitId, EnergyUnitId]
    ) -> tuple[EnergyConnection, ...]:
        """A node's incoming connections, restricted to the single active one for exclusive-input nodes."""
        if node_id not in self._topology.get_exclusive_input_nodes():
            return self._topology.get_incoming_connections(node_id)
        active_candidate_id = active_connections[node_id]
        return (self._topology.get_connection(active_candidate_id, node_id),)

    def _zero_inactive_candidates(
        self,
        active_connections: Mapping[EnergyUnitId, EnergyUnitId],
        connection_energy: dict[EnergyConnectionId, Energy],
    ) -> None:
        """Give every non-active candidate connection of an exclusive-input node zero energy, so upstream nodes
        that only supply an inactive candidate still have a connection energy to look up."""
        for node_id, active_candidate_id in active_connections.items():
            active_connection = self._topology.get_connection(active_candidate_id, node_id)
            for connection in self._topology.get_incoming_connections(node_id):
                if connection.id != active_connection.id:
                    connection_energy.setdefault(connection.id, connection.energy_type(value=0))

    def _validate_active_connections(self, active_connections: Mapping[EnergyUnitId, EnergyUnitId]) -> None:
        exclusive_input_nodes = self._topology.get_exclusive_input_nodes()
        provided_ids = set(active_connections)

        missing_ids = exclusive_input_nodes - provided_ids
        if missing_ids:
            raise InvalidEnergyNetworkInputError(
                f"Missing active connections for exclusive-input energy units: "
                f"{', '.join(self._format_energy_unit_reference(node_id) for node_id in sorted(missing_ids, key=str))}"
            )

        unexpected_ids = provided_ids - exclusive_input_nodes
        if unexpected_ids:
            raise InvalidEnergyNetworkInputError(
                f"Unexpected active connections for energy units that do not have exclusive input: "
                f"{', '.join(self._format_energy_unit_reference(node_id) for node_id in sorted(unexpected_ids, key=str))}"
            )

        for node_id, active_candidate_id in active_connections.items():
            if active_candidate_id not in self._topology.get_predecessors(node_id):
                raise InvalidEnergyNetworkInputError(
                    f"Active connection for {self._format_energy_unit_reference(node_id)} names "
                    f"{self._format_energy_unit_reference(active_candidate_id)}, which is not a predecessor"
                )

    def _validate_connection_demands(
        self,
        connection_demands: dict[EnergyConnectionId, Energy],
        active_connections: Mapping[EnergyUnitId, EnergyUnitId],
    ) -> None:
        consumer_ids = self._topology.get_leaf_nodes()
        consumer_connection_ids = {
            connection.id
            for node_id in consumer_ids
            for connection in self._incoming_connections_for(node_id, active_connections)
        }
        self._validate_connection_ids(
            provided_ids=set(connection_demands),
            expected_ids=consumer_connection_ids,
            value_name="connection demands",
        )
        self._validate_energy_types(connection_demands)

    def _validate_connection_ids(
        self,
        provided_ids: set[EnergyConnectionId],
        expected_ids: set[EnergyConnectionId],
        value_name: str,
    ) -> None:
        missing_ids = expected_ids - provided_ids
        if missing_ids:
            raise InvalidEnergyNetworkInputError(
                f"Missing {value_name} for connections: {self._format_connection_references(missing_ids)}"
            )

        unexpected_ids = provided_ids - expected_ids
        if unexpected_ids:
            raise InvalidEnergyNetworkInputError(
                f"Unexpected {value_name} for connections: {self._format_connection_references(unexpected_ids)}"
            )

    def _validate_energy_types(self, connection_demands: dict[EnergyConnectionId, Energy]) -> None:
        for connection_id, demand in connection_demands.items():
            connection = self._topology.get_connection_by_id(connection_id)
            expected_type = connection.energy_type

            if type(demand) is not expected_type:
                raise InvalidEnergyNetworkInputError(
                    f"Consumer demand for connection {self._format_connection_reference(connection_id)} requires "
                    f"{expected_type.__name__}, got {type(demand).__name__}"
                )

    def _format_connection_references(self, connection_ids: set[EnergyConnectionId]) -> str:
        return ", ".join(
            self._format_connection_reference(connection_id) for connection_id in sorted(connection_ids, key=str)
        )

    def _format_connection_reference(self, connection_id: EnergyConnectionId) -> str:
        try:
            connection = self._topology.get_connection_by_id(connection_id)
        except KeyError:
            return str(connection_id)
        return (
            f"{self._format_energy_unit_reference(connection.source_id)} -> "
            f"{self._format_energy_unit_reference(connection.target_id)} ({connection_id})"
        )

    def _format_energy_unit_reference(self, node_id: EnergyUnitId, energy_unit_name: str | None = None) -> str:
        return f"'{energy_unit_name}' ({node_id})" if energy_unit_name is not None else str(node_id)
