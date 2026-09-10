from collections.abc import Iterable

from libecalc.energy import Consumer, Converter, Energy, EnergyUnit, EnergyUnitId
from libecalc.energy.energy_units import Junction, Transporter
from libecalc.energy.errors import (
    EnergyAllocationRequiredError,
    InvalidEnergyNetworkError,
    InvalidEnergyNetworkEvaluationInputError,
)
from libecalc.energy.network import EnergyNetwork


class EnergyNetworkEvaluation:
    def __init__(
        self,
        energy_network: EnergyNetwork,
        energy_units: Iterable[EnergyUnit],
        consumer_demands: dict[EnergyUnitId, Energy],
    ) -> None:
        self._energy_network = energy_network
        self._energy_units: dict[EnergyUnitId, EnergyUnit] = {}

        for energy_unit in energy_units:
            energy_unit_id = energy_unit.get_id()
            if energy_unit_id in self._energy_units:
                raise InvalidEnergyNetworkEvaluationInputError(f"Duplicate energy unit ID: {energy_unit_id}")

            self._energy_units[energy_unit_id] = energy_unit

        self._consumer_demands = dict(consumer_demands)
        self._validate_inputs()

    # Per-node energy
    def get_input_energy(
        self,
        node_id: EnergyUnitId,
    ) -> Energy | None:
        node = self._energy_units[node_id]

        if isinstance(node, Consumer):
            return self._consumer_demands[node_id]

        if node.get_input_energy_type() is None:
            return None

        output_energy = self.get_output_energy(node_id)

        if output_energy is None:
            raise InvalidEnergyNetworkError(f"Energy unit {node_id} has no output energy")

        if isinstance(node, Junction):
            return output_energy

        if isinstance(node, (Converter, Transporter)):
            return node.get_input_energy(output_energy)

        raise InvalidEnergyNetworkError(f"Unsupported energy unit type: {type(node).__name__}")

    def get_output_energy(
        self,
        node_id: EnergyUnitId,
    ) -> Energy | None:
        node = self._energy_units[node_id]
        output_type = node.get_output_energy_type()

        if output_type is None:
            return None

        output_energy = output_type(value=0)

        # A source, converter, transporter, or junction outputs the combined input
        # energy of its successors.
        for successor_id in self._energy_network.get_successors(node_id):
            successor_input_energy = self.get_input_energy(successor_id)

            if successor_input_energy is None:
                raise InvalidEnergyNetworkError(f"Energy unit {successor_id} has no input energy")

            # Positive demand with multiple predecessors requires allocation.
            if successor_input_energy.value > 0 and len(self._energy_network.get_predecessors(successor_id)) > 1:
                raise EnergyAllocationRequiredError(
                    f"Cannot calculate output energy for unit {node_id}: "
                    f"successor {successor_id} has {len(self._energy_network.get_predecessors(successor_id))} predecessors, "
                    "so an allocation strategy is required"
                )

            output_energy += successor_input_energy

        return output_energy

    def _validate_inputs(self) -> None:
        network_nodes = {node.get_id(): node for node in self._energy_network.get_nodes()}
        nodes = self._energy_units

        self._validate_energy_units(network_nodes)

        consumer_ids = {node_id for node_id, node in nodes.items() if isinstance(node, Consumer)}

        self._validate_consumer_demands(
            provided_ids=set(self._consumer_demands),
            expected_ids=consumer_ids,
            value_name="consumer demands",
            nodes=nodes,
        )

        self._validate_energy_types(nodes)

    def _validate_energy_units(self, network_nodes: dict[EnergyUnitId, EnergyUnit]) -> None:
        self._validate_node_ids(
            provided_ids=set(self._energy_units),
            expected_ids=set(network_nodes),
            value_name="energy units",
            nodes=network_nodes,
        )

        for node_id, energy_unit in self._energy_units.items():
            network_node = network_nodes[node_id]
            if (
                energy_unit.get_input_energy_type() is not network_node.get_input_energy_type()
                or energy_unit.get_output_energy_type() is not network_node.get_output_energy_type()
            ):
                raise InvalidEnergyNetworkEvaluationInputError(
                    f"Energy unit '{energy_unit.get_name()}' ({node_id}) has energy types that do not match the network"
                )

    def _validate_consumer_demands(
        self,
        provided_ids: set[EnergyUnitId],
        expected_ids: set[EnergyUnitId],
        value_name: str,
        nodes: dict[EnergyUnitId, EnergyUnit],
    ) -> None:
        self._validate_node_ids(provided_ids, expected_ids, value_name, nodes)

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

    def _validate_energy_types(
        self,
        nodes: dict[EnergyUnitId, EnergyUnit],
    ) -> None:
        for node_id, demand in self._consumer_demands.items():
            node = nodes[node_id]
            assert isinstance(node, Consumer)
            expected_type = node.get_input_energy_type()

            if type(demand) is not expected_type:
                raise InvalidEnergyNetworkEvaluationInputError(
                    f"Consumer '{node.get_name()}' ({node_id}) requires "
                    f"{expected_type.__name__}, got {type(demand).__name__}"
                )

    @staticmethod
    def _format_node_references(
        node_ids: set[EnergyUnitId],
        nodes: dict[EnergyUnitId, EnergyUnit],
    ) -> str:
        return ", ".join(
            (f"'{nodes[node_id].get_name()}' ({node_id})" if node_id in nodes else str(node_id))
            for node_id in sorted(node_ids, key=str)
        )
