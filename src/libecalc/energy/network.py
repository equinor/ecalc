from collections.abc import Iterable
from graphlib import CycleError, TopologicalSorter
from typing import NewType, Self
from uuid import UUID

from libecalc.common.ddd import value_object
from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.energy.consumer import Consumer
from libecalc.energy.converter import Converter
from libecalc.energy.energy_types import Energy
from libecalc.energy.energy_unit import EnergyUnit, EnergyUnitId
from libecalc.energy.energy_units import Junction, Transporter
from libecalc.energy.errors import EnergyAllocationRequiredError, InvalidEnergyNetworkError
from libecalc.energy.source import Source

# Role groups the network asks about. Each question has one definition, so a new role
# cannot be handled in one place and forgotten in another.
ProvidesEnergy = Source | Converter | Transporter | Junction
RequiresEnergy = Consumer | Converter | Transporter | Junction
DerivesInputFromOutput = Junction | Converter | Transporter
HasCapacity = Source | Converter | Transporter


@value_object
class EnergyConnection:
    """A directed connection between two energy units."""

    source_id: EnergyUnitId
    target_id: EnergyUnitId


EnergyNetworkId = NewType("EnergyNetworkId", UUID)


class EnergyNetwork:
    """A validated, directed acyclic graph of typed energy units."""

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

        if isinstance(node, DerivesInputFromOutput):
            output_energy = self.get_output_energy(node_id)

            if output_energy is None:
                raise InvalidEnergyNetworkError(f"Energy unit {node_id} has no output energy")

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

        if not isinstance(node, ProvidesEnergy):
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
                    f"successor {successor_id} has {len(self.get_predecessors(successor_id))} predecessors, "
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

        if isinstance(unit, HasCapacity):
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
