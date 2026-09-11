from collections.abc import Iterable

from libecalc.energy import Consumer, Converter, Energy, EnergyUnit, EnergyUnitId, Source
from libecalc.energy.dispatch import Candidate
from libecalc.energy.energy_units import Junction, Transporter
from libecalc.energy.errors import (
    EnergyAllocationRequiredError,
    InvalidEnergyNetworkError,
    InvalidEnergyNetworkEvaluationInputError,
)
from libecalc.energy.network import EnergyConnectionId, EnergyNetwork


class EnergyNetworkEvaluation:
    def __init__(
        self,
        energy_network: EnergyNetwork,
        energy_units: Iterable[EnergyUnit],
    ) -> None:
        self._energy_network = energy_network
        self._energy_units: dict[EnergyUnitId, EnergyUnit] = {}

        for energy_unit in energy_units:
            energy_unit_id = energy_unit.get_id()
            if energy_unit_id in self._energy_units:
                raise InvalidEnergyNetworkEvaluationInputError(
                    f"Duplicate energy unit: {self._format_energy_unit_reference(energy_unit_id, energy_unit)}"
                )

            self._energy_units[energy_unit_id] = energy_unit

        # _validate_energy_units must run first: the validators below look up predecessors for every
        # unit, which raises KeyError for a unit the network does not know.
        self._validate_energy_units()
        self._validate_fan_in()
        self._validate_dispatch()

    def propagate_energy(
        self, connection_demands: dict[EnergyConnectionId, Energy]
    ) -> dict[EnergyConnectionId, Energy]:
        """Calculate connection energy from demands on consumer-targeting connections."""
        self._validate_connection_demands(connection_demands)

        connection_energy: dict[EnergyConnectionId, Energy] = {}
        for node_id in reversed(self._energy_network.get_topological_order()):
            node = self._energy_units[node_id]
            if isinstance(node, Consumer):
                for predecessor_id in self._energy_network.get_predecessors(node_id):
                    connection = self._energy_network.get_connection(predecessor_id, node_id)
                    connection_energy[connection.id] = connection_demands[connection.id]
                continue

            input_energy = self._get_input_energy(node_id, connection_energy)
            if input_energy is None:
                continue

            predecessors = self._energy_network.get_predecessors(node_id)

            # Consumers were handled above, and validation rejects fan-in into anything but a junction,
            # so several predecessors here means a junction that splits its demand between them.
            if len(predecessors) > 1:
                for predecessor_id, share in self._allocate(node_id, input_energy).items():
                    connection = self._energy_network.get_connection(predecessor_id, node_id)
                    connection_energy[connection.id] = share
                continue

            # A single predecessor supplies all the energy.
            for predecessor_id in predecessors:
                connection = self._energy_network.get_connection(predecessor_id, node_id)
                connection_energy[connection.id] = input_energy

        return connection_energy

    def _allocate(self, junction_id: EnergyUnitId, demand: Energy) -> dict[EnergyUnitId, Energy]:
        """Split a junction's demand between the candidates feeding it.

        Validation has already established that the node is a junction with a strategy whose candidates
        are exactly its predecessors.
        """
        junction = self._energy_units[junction_id]
        assert isinstance(junction, Junction)

        strategy = junction.get_dispatch_strategy()
        assert strategy is not None

        candidates = tuple(
            Candidate(candidate_id=predecessor_id, available=self._capacity(predecessor_id))
            for predecessor_id in self._energy_network.get_predecessors(junction_id)
        )
        return strategy.allocate(demand=demand, candidates=candidates)

    def _capacity(self, node_id: EnergyUnitId) -> Energy | None:
        """What a node is rated to supply. None means unlimited."""
        node = self._energy_units[node_id]
        if isinstance(node, (Source, Converter, Transporter)):
            return node.capacity()
        return None

    def _get_input_energy(
        self,
        node_id: EnergyUnitId,
        connection_energy: dict[EnergyConnectionId, Energy],
    ) -> Energy | None:
        node = self._energy_units[node_id]
        input_energy_type = node.get_input_energy_type()
        if input_energy_type is None:
            return None

        output_energy_type = node.get_output_energy_type()
        if output_energy_type is None:
            raise InvalidEnergyNetworkError(
                f"Energy unit {self._format_energy_unit_reference(node_id)} has no output energy"
            )

        output_energy = output_energy_type(0)
        for successor_id in self._energy_network.get_successors(node_id):
            connection = self._energy_network.get_connection(node_id, successor_id)
            output_energy += connection_energy[connection.id]

        if isinstance(node, Junction):
            return output_energy
        if isinstance(node, (Converter, Transporter)):
            return node.get_input_energy(output_energy)
        raise InvalidEnergyNetworkError(
            f"Unsupported energy unit type for {self._format_energy_unit_reference(node_id)}: {type(node).__name__}"
        )

    def _validate_energy_units(self) -> None:
        self._validate_node_ids(
            provided_ids=set(self._energy_units),
            expected_ids=set(self._energy_network.get_topological_order()),
            value_name="energy units",
            nodes=self._energy_units,
        )

        for node_id, energy_unit in self._energy_units.items():
            input_types = {
                connection.energy_type
                for connection in self._energy_network.get_connections()
                if connection.target_id == node_id
            }
            output_types = {
                connection.energy_type
                for connection in self._energy_network.get_connections()
                if connection.source_id == node_id
            }
            if (input_types and energy_unit.get_input_energy_type() not in input_types) or (
                output_types and energy_unit.get_output_energy_type() not in output_types
            ):
                raise InvalidEnergyNetworkEvaluationInputError(
                    f"Energy unit {self._format_energy_unit_reference(node_id)} has energy types that do not match the network"
                )

    def _validate_fan_in(self) -> None:
        """Only a junction may be fed by more than one predecessor.

        The YAML schema agrees: INPUT is a list for a junction and a single reference for everything
        else. Without this rule a converter or consumer with two supplies would reach _allocate,
        which assumes a junction, and fail there instead of at construction.
        """
        for node_id, energy_unit in self._energy_units.items():
            if isinstance(energy_unit, Junction):
                continue

            predecessor_count = len(self._energy_network.get_predecessors(node_id))
            if predecessor_count > 1:
                raise InvalidEnergyNetworkError(
                    f"Energy unit {self._format_energy_unit_reference(node_id, energy_unit)} has "
                    f"{predecessor_count} predecessors; only junctions support fan-in"
                )

    def _validate_dispatch(self) -> None:
        """Reject a junction whose demand cannot be split, before any energy is propagated.

        Fan-in into anything other than a junction is rejected by _validate_fan_in, so only
        junctions are of interest here.
        """
        for node_id, energy_unit in self._energy_units.items():
            if not isinstance(energy_unit, Junction):
                continue

            predecessors = self._energy_network.get_predecessors(node_id)
            strategy = energy_unit.get_dispatch_strategy()

            # Checked for any predecessor count, not just fan-in: a single candidate decides nothing,
            # but naming a node that does not feed this junction is still an error.
            if strategy is not None and strategy.get_candidate_ids() != predecessors:
                raise InvalidEnergyNetworkError(
                    f"Dispatch strategy candidate IDs for junction "
                    f"{self._format_energy_unit_reference(node_id, energy_unit)} must match its predecessors"
                )

            if len(predecessors) <= 1:
                continue

            if strategy is None:
                raise EnergyAllocationRequiredError(
                    f"Junction {self._format_energy_unit_reference(node_id, energy_unit)} has "
                    f"{len(predecessors)} predecessors and requires a dispatch strategy"
                )

            for predecessor_id in predecessors:
                successor_count = len(self._energy_network.get_successors(predecessor_id))
                if successor_count != 1:
                    raise InvalidEnergyNetworkError(
                        f"Predecessor {self._format_energy_unit_reference(predecessor_id)} feeds dispatched "
                        f"junction {self._format_energy_unit_reference(node_id, energy_unit)} and must have "
                        f"exactly one successor, got {successor_count}"
                    )

    def _validate_connection_demands(self, connection_demands: dict[EnergyConnectionId, Energy]) -> None:
        consumer_connection_ids = {
            connection.id
            for connection in self._energy_network.get_connections()
            if isinstance(self._energy_units[connection.target_id], Consumer)
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
        nodes: dict[EnergyUnitId, EnergyUnit],
    ) -> None:
        missing_ids = expected_ids - provided_ids
        if missing_ids:
            node_references = self._format_node_references(
                node_ids=missing_ids,
                nodes=nodes,
            )
            raise InvalidEnergyNetworkEvaluationInputError(f"Missing {value_name} for nodes: {node_references}")

        unexpected_ids = provided_ids - expected_ids
        if unexpected_ids:
            node_references = self._format_node_references(
                node_ids=unexpected_ids,
                nodes=nodes,
            )
            raise InvalidEnergyNetworkEvaluationInputError(f"Unexpected {value_name} for nodes: {node_references}")

    def _validate_connection_ids(
        self,
        provided_ids: set[EnergyConnectionId],
        expected_ids: set[EnergyConnectionId],
        value_name: str,
    ) -> None:
        missing_ids = expected_ids - provided_ids
        if missing_ids:
            raise InvalidEnergyNetworkEvaluationInputError(
                f"Missing {value_name} for connections: {self._format_connection_references(missing_ids)}"
            )

        unexpected_ids = provided_ids - expected_ids
        if unexpected_ids:
            raise InvalidEnergyNetworkEvaluationInputError(
                f"Unexpected {value_name} for connections: {self._format_connection_references(unexpected_ids)}"
            )

    def _validate_energy_types(self, connection_demands: dict[EnergyConnectionId, Energy]) -> None:
        for connection_id, demand in connection_demands.items():
            connection = self._energy_network.get_connection_by_id(connection_id)
            expected_type = connection.energy_type

            if type(demand) is not expected_type:
                raise InvalidEnergyNetworkEvaluationInputError(
                    f"Consumer demand for connection {self._format_connection_reference(connection_id)} requires "
                    f"{expected_type.__name__}, got {type(demand).__name__}"
                )

    def _format_connection_references(self, connection_ids: set[EnergyConnectionId]) -> str:
        return ", ".join(
            self._format_connection_reference(connection_id) for connection_id in sorted(connection_ids, key=str)
        )

    def _format_connection_reference(self, connection_id: EnergyConnectionId) -> str:
        try:
            connection = self._energy_network.get_connection_by_id(connection_id)
        except KeyError:
            return str(connection_id)
        return (
            f"{self._format_energy_unit_reference(connection.source_id)} -> "
            f"{self._format_energy_unit_reference(connection.target_id)} ({connection_id})"
        )

    def _format_node_references(
        self,
        node_ids: set[EnergyUnitId],
        nodes: dict[EnergyUnitId, EnergyUnit],
    ) -> str:
        return ", ".join(
            self._format_energy_unit_reference(node_id, nodes.get(node_id)) for node_id in sorted(node_ids, key=str)
        )

    def _format_energy_unit_reference(self, node_id: EnergyUnitId, energy_unit: EnergyUnit | None = None) -> str:
        energy_unit = energy_unit or self._energy_units.get(node_id)
        return f"'{energy_unit.get_name()}' ({node_id})" if energy_unit is not None else str(node_id)
