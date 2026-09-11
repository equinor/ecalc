from collections.abc import Iterable

from libecalc.energy import Consumer, Converter, Energy, EnergyUnit, EnergyUnitId
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

        self._validate_energy_units()

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
            if input_energy.value > 0 and len(predecessors) > 1:
                raise EnergyAllocationRequiredError(
                    f"Cannot calculate input energy for unit {self._format_energy_unit_reference(node_id)}: "
                    f"it has {len(predecessors)} predecessors, so an allocation strategy is required"
                )

            for predecessor_id in predecessors:
                connection = self._energy_network.get_connection(predecessor_id, node_id)
                connection_energy[connection.id] = input_energy

        return connection_energy

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
