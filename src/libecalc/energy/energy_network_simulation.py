import abc
from collections.abc import Iterable, Sequence
from typing import Any

from libecalc.energy import Converter, Energy, EnergyUnit, EnergyUnitId
from libecalc.energy.dispatch import Candidate
from libecalc.energy.energy_network import EnergyNetwork
from libecalc.energy.energy_network_topology import EnergyConnection, EnergyConnectionId, EnergyNetworkTopology
from libecalc.energy.energy_unit_state import EnergyUnitState
from libecalc.energy.energy_units import Junction, Transporter
from libecalc.energy.errors import (
    EnergyAllocationRequiredError,
    FanInNotSupportedError,
    InvalidEnergyNetworkError,
    InvalidEnergyNetworkInputError,
)


class EnergyUnitFactory(abc.ABC):
    @abc.abstractmethod
    def get_id(self) -> EnergyUnitId: ...

    @abc.abstractmethod
    def get_name(self) -> str: ...

    @abc.abstractmethod
    def create(self, demand: Energy, capacity: Energy | None, **extra: Any) -> EnergyUnit: ...


def _sum_connection_energy(
    *,
    connections: Sequence[EnergyConnection],
    connection_energy: dict[EnergyConnectionId, Energy],
) -> Energy:
    total = connection_energy[connections[0].id]
    for connection in connections[1:]:
        total += connection_energy[connection.id]
    return total


class EnergyNetworkSimulation:
    def __init__(
        self,
        topology: EnergyNetworkTopology,
        energy_unit_factories: Iterable[EnergyUnitFactory],
        junctions: dict[EnergyUnitId, Junction],
    ) -> None:
        self._topology = topology
        self._energy_unit_factories = {}
        self._junctions = junctions

        for energy_unit_factory in energy_unit_factories:
            energy_unit_id = energy_unit_factory.get_id()
            if energy_unit_id in self._energy_unit_factories:
                raise InvalidEnergyNetworkInputError(
                    f"Duplicate energy unit: {self._format_energy_unit_reference(energy_unit_id, energy_unit_factory.get_name())}"
                )

            self._energy_unit_factories[energy_unit_id] = energy_unit_factory

        self._validate_fan_in()
        self._validate_dispatch()

    def run(
        self,
        connection_demands: dict[EnergyConnectionId, Energy],
        capacities: dict[EnergyUnitId, Energy] | None = None,
        **extra: Any,
    ) -> EnergyNetwork:
        """Calculate connection energy and unit states from demands on consumer-targeting connections.

        Demand is propagated upstream in reverse topological order, so every node is visited only after all of
        its outgoing connections are known. A node's output is the sum of the energy on those connections; from
        that we derive the energy it draws from its predecessors. Converters and transporters translate output
        into required input, while junctions split their output across the predecessors feeding them.

        `capacities` is consulted where a junction dispatches demand across several candidates and when evaluating
        capacity failures; a candidate absent from it is treated as unlimited, as elsewhere.
        """
        self._validate_connection_demands(connection_demands)
        capacities = capacities or {}
        extra = extra or {}

        unit_states: dict[EnergyUnitId, EnergyUnitState] = {}
        connection_energy: dict[EnergyConnectionId, Energy] = dict(connection_demands)

        for node_id in reversed(self._topology.get_topological_order()):
            outgoing_connections = self._topology.get_outgoing_connections(node_id)
            incoming_connections = self._topology.get_incoming_connections(node_id)

            if not outgoing_connections:
                if not incoming_connections:
                    continue

                consumed = _sum_connection_energy(
                    connections=incoming_connections,
                    connection_energy=connection_energy,
                )
                unit_states[node_id] = EnergyUnitState(
                    output_energy=None,
                    input_energy=consumed,
                    capacity=None,
                )
                continue

            demand = _sum_connection_energy(
                connections=outgoing_connections,
                connection_energy=connection_energy,
            )

            # Junctions are nodes in the topology but are not created per operational point, so they are handled
            # here rather than through a factory: they are lossless and split their output across predecessors.
            if node_id in self._junctions:
                if len(incoming_connections) <= 1:
                    for connection in incoming_connections:
                        connection_energy[connection.id] = demand
                else:
                    junction = self._junctions[node_id]
                    allocations = self._allocate(junction=junction, demand=demand, capacities=capacities)
                    for connection in incoming_connections:
                        connection_energy[connection.id] = allocations[connection.source_id]

                unit_states[node_id] = EnergyUnitState(
                    output_energy=demand,
                    input_energy=demand if incoming_connections else None,
                    capacity=None,
                )
            else:
                energy_unit_factory = self._energy_unit_factories[node_id]
                energy_unit = energy_unit_factory.create(
                    demand=demand,
                    capacity=capacities.get(node_id),
                    **extra,
                )

                input_energy: Energy | None = None
                if incoming_connections:
                    # Only converters and transporters draw input; sources have no predecessors.
                    assert isinstance(energy_unit, Converter | Transporter)
                    input_energy = energy_unit.get_input_energy()
                    for connection in incoming_connections:
                        connection_energy[connection.id] = input_energy

                unit_states[node_id] = EnergyUnitState(
                    output_energy=demand,
                    input_energy=input_energy,
                    capacity=capacities.get(node_id),
                    failures=tuple(energy_unit.get_failures()),
                )

        return EnergyNetwork(
            topology=self._topology,
            unit_states=unit_states,
            connection_energy=connection_energy,
        )

    def _allocate(
        self,
        junction: Junction,
        demand: Energy,
        capacities: dict[EnergyUnitId, Energy],
    ) -> dict[EnergyUnitId, Energy]:
        """Split a junction's demand between the candidates feeding it.

        Validation has already established that the node is a junction with a strategy whose candidates
        are exactly its predecessors. A candidate absent from `capacities` is unlimited.
        """
        strategy = junction.get_dispatch_strategy()
        assert strategy is not None

        candidates = tuple(
            Candidate(candidate_id=predecessor_id, available=capacities.get(predecessor_id))
            for predecessor_id in self._topology.get_predecessors(junction.get_id())
        )
        return strategy.allocate(demand=demand, candidates=candidates)

    def _validate_fan_in(self) -> None:
        """Only a junction may be fed by more than one predecessor.

        The YAML schema agrees: INPUT is a list for a junction and a single reference for everything
        else. Without this rule a converter or consumer with two supplies would reach _allocate,
        which assumes a junction, and fail there instead of at construction.

        Every non-junction node is checked, not just factories, so a consumer fanned into by several
        supplies is rejected too. The raised error carries the node identity; the simulation has no
        names, so a caller can resolve one and enrich the message.
        """
        for node_id in self._topology.get_nodes():
            if node_id in self._junctions:
                continue
            predecessor_count = len(self._topology.get_predecessors(node_id))
            if predecessor_count > 1:
                raise FanInNotSupportedError(node_id=node_id, predecessor_count=predecessor_count)

    def _validate_dispatch(self) -> None:
        """Reject a junction whose demand cannot be split, before any energy is propagated.

        Fan-in into anything other than a junction is rejected by _validate_fan_in, so only
        junctions are of interest here.
        """
        for node_id, energy_unit in self._junctions.items():
            predecessors = self._topology.get_predecessors(node_id)
            strategy = energy_unit.get_dispatch_strategy()

            # Checked for any predecessor count, not just fan-in: a single candidate decides nothing,
            # but naming a node that does not feed this junction is still an error.
            if strategy is not None and strategy.get_candidate_ids() != predecessors:
                raise InvalidEnergyNetworkError(
                    f"Dispatch strategy candidate IDs for junction "
                    f"{self._format_energy_unit_reference(node_id, energy_unit.get_name())} must match its predecessors"
                )

            if len(predecessors) <= 1:
                continue

            if strategy is None:
                raise EnergyAllocationRequiredError(
                    f"Junction {self._format_energy_unit_reference(node_id, energy_unit.get_name())} has "
                    f"{len(predecessors)} predecessors and requires a dispatch strategy"
                )

            for predecessor_id in predecessors:
                successor_count = len(self._topology.get_successors(predecessor_id))
                if successor_count != 1:
                    raise InvalidEnergyNetworkError(
                        f"Predecessor {self._format_energy_unit_reference(predecessor_id)} feeds dispatched "
                        f"junction {self._format_energy_unit_reference(node_id, energy_unit.get_name())} and must have "
                        f"exactly one successor, got {successor_count}"
                    )

    def _validate_connection_demands(self, connection_demands: dict[EnergyConnectionId, Energy]) -> None:
        consumer_ids = self._topology.get_leaf_nodes()
        consumer_connection_ids = {
            connection.id for connection in self._topology.get_connections() if connection.target_id in consumer_ids
        }
        self._validate_connection_ids(
            provided_ids=set(connection_demands),
            expected_ids=consumer_connection_ids,
            value_name="connection demands",
        )
        self._validate_energy_types(connection_demands)

    def _validate_node_ids(
        self,
        provided_ids: set[EnergyUnitId],
        expected_ids: set[EnergyUnitId],
        value_name: str,
        nodes: dict[EnergyUnitId, EnergyUnitFactory],
    ) -> None:
        missing_ids = expected_ids - provided_ids
        if missing_ids:
            node_references = self._format_node_references(
                node_ids=missing_ids,
                nodes=nodes,
            )
            raise InvalidEnergyNetworkInputError(f"Missing {value_name} for nodes: {node_references}")

        unexpected_ids = provided_ids - expected_ids
        if unexpected_ids:
            node_references = self._format_node_references(
                node_ids=unexpected_ids,
                nodes=nodes,
            )
            raise InvalidEnergyNetworkInputError(f"Unexpected {value_name} for nodes: {node_references}")

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

    def _format_node_references(
        self,
        node_ids: set[EnergyUnitId],
        nodes: dict[EnergyUnitId, EnergyUnitFactory],
    ) -> str:
        refs = []
        for node_id in sorted(node_ids, key=str):
            node = nodes.get(node_id)
            refs.append(self._format_energy_unit_reference(node_id, node.get_name() if node else None))
        return ", ".join(refs)

    def _format_energy_unit_reference(self, node_id: EnergyUnitId, energy_unit_name: str | None = None) -> str:
        return f"'{energy_unit_name}' ({node_id})" if energy_unit_name is not None else str(node_id)
