from collections.abc import Iterable
from graphlib import CycleError, TopologicalSorter

from libecalc.common.ddd import value_object
from libecalc.energy.consumer import Consumer
from libecalc.energy.converter import Converter
from libecalc.energy.energy_types import Energy
from libecalc.energy.energy_unit import EnergyUnitId
from libecalc.energy.energy_units import Junction, Transporter
from libecalc.energy.errors import EnergyAllocationRequiredError, InvalidEnergyNetworkError
from libecalc.energy.source import Source

type EnergyNetworkNode = Consumer | Source | Converter | Transporter | Junction


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

    # Node access
    def get_node(
        self,
        node_id: EnergyUnitId,
    ) -> EnergyNetworkNode:
        return self._nodes[node_id]

    def get_nodes(self) -> tuple[EnergyNetworkNode, ...]:
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

    # Per-unit energy
    def get_input_energy(
        self,
        node_id: EnergyUnitId,
    ) -> Energy | None:
        node = self.get_node(node_id)

        # A consumer defines its own input energy.
        if isinstance(node, Consumer):
            return node.get_input_energy()

        # A source has no input energy
        if isinstance(node, Source):
            return None

        if isinstance(node, (Junction, Converter)):
            output_energy = self.get_output_energy(node_id)

            if output_energy is None:
                raise InvalidEnergyNetworkError(f"Energy unit {node_id} has no output energy")

            # A junction passes energy through without conversion.
            if isinstance(node, Junction):
                return output_energy

            # A converter derives its input energy from its output energy.
            if isinstance(node, Converter):
                return node.get_input_energy(output_energy)

        raise InvalidEnergyNetworkError(f"Unsupported energy unit type: {type(node).__name__}")

    def get_output_energy(
        self,
        node_id: EnergyUnitId,
    ) -> Energy | None:
        node = self.get_node(node_id)

        # A consumer has no output energy within the network boundary.
        if isinstance(node, Consumer):
            return None

        if not isinstance(node, (Source, Converter, Transporter, Junction)):
            raise InvalidEnergyNetworkError(f"Unsupported energy unit type: {type(node).__name__}")

        output_energy = node.get_output_energy_type()(value=0)

        # A source, converter, transporter, or junction outputs the combined input
        # energy of its successors.
        for successor_id in self.get_successors(node_id):
            successor_input_energy = self.get_input_energy(successor_id)

            if successor_input_energy is None:
                raise InvalidEnergyNetworkError(f"Energy unit {successor_id} has no input energy")

            # Positive demand with multiple predecessors requires allocation.
            if successor_input_energy.value > 0 and len(self.get_predecessors(successor_id)) > 1:
                raise EnergyAllocationRequiredError(
                    f"Cannot calculate output energy for unit {node_id}: "
                    f"successor {successor_id} has {len(self._predecessors)} predecessors, "
                    "so an allocation strategy is required"
                )

            output_energy += successor_input_energy

        return output_energy

    # Capacity and feasibility
    def get_capacity(
        self,
        unit_id: EnergyUnitId,
    ) -> Energy | None:
        unit = self.get_node(unit_id)

        if isinstance(unit, (Source, Converter, Transporter)):
            return unit.capacity()

        return None

    def is_capacity_exceeded(
        self,
        unit_id: EnergyUnitId,
    ) -> bool:
        capacity = self.get_capacity(unit_id)

        if capacity is None:
            return False

        output_energy = self.get_output_energy(unit_id)

        if output_energy is None:
            raise InvalidEnergyNetworkError(f"Energy unit {unit_id} has capacity but no output energy")

        return output_energy.value > capacity.value

    def is_feasible(self) -> bool:
        return not any(self.is_capacity_exceeded(unit_id) for unit_id in self.get_topological_order())

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

        output_type = self._get_output_type(source)
        input_type = self._get_input_type(target)

        if output_type is not input_type:
            raise InvalidEnergyNetworkError(
                f"Incompatible energy types: {output_type.__name__} -> {input_type.__name__}"
            )

    def _validate_required_predecessors(self) -> None:
        for unit_id, unit in self._nodes.items():
            if isinstance(unit, (Consumer, Converter, Junction)) and not self._predecessors[unit_id]:
                raise InvalidEnergyNetworkError(f"Energy unit {unit_id} requires input energy but has no predecessor")

    @staticmethod
    def _get_output_type(
        node: EnergyNetworkNode,
    ) -> type[Energy]:
        if not isinstance(node, (Source, Converter, Transporter, Junction)):
            raise InvalidEnergyNetworkError(
                f"Source node of type '{type(node).__name__}' with id '{node.get_id()}' provides no energy"
            )

        return node.get_output_energy_type()

    @staticmethod
    def _get_input_type(
        node: EnergyNetworkNode,
    ) -> type[Energy]:
        if not isinstance(node, (Consumer, Converter, Transporter, Junction)):
            raise InvalidEnergyNetworkError(
                f"Target node of type '{type(node).__name__}' with id '{node.get_id()}' requires no energy"
            )

        return node.get_input_energy_type()

    def _create_topological_order(
        self,
    ) -> tuple[EnergyUnitId, ...]:
        try:
            return tuple(TopologicalSorter(self._predecessors).static_order())
        except CycleError as error:
            raise InvalidEnergyNetworkError("Energy network cannot be cyclic") from error
