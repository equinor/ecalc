from collections.abc import Iterable
from graphlib import CycleError, TopologicalSorter

from libecalc.common.ddd import value_object
from libecalc.energy.dispatch import ProviderAvailability
from libecalc.energy.energy_types import Energy
from libecalc.energy.energy_unit import EnergyUnitId
from libecalc.energy.errors import EnergyAllocationRequiredError, InvalidEnergyNetworkError
from libecalc.energy.roles import Consumer, DerivedInputProvider, Junction, Provider

type EnergyNetworkNode = Consumer | Provider


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

        self._predecessors: dict[EnergyUnitId, dict[EnergyUnitId, None]] = {node_id: {} for node_id in self._nodes}
        self._successors: dict[EnergyUnitId, dict[EnergyUnitId, None]] = {node_id: {} for node_id in self._nodes}

        self._add_connections(connections)
        self._validate_required_predecessors()
        self._validate_predecessor_limits()
        self._validate_dispatch()
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

        if isinstance(node, DerivedInputProvider):
            # This node's input is derived from the output it is asked to deliver.
            requested_output = self.get_output_energy(node_id)
            if requested_output is None:
                raise InvalidEnergyNetworkError(f"Energy unit {node_id} has no output energy")
            return node.get_input_energy(requested_output)

        if isinstance(node, Consumer):
            # A pure sink's own demand is fixed, independent of any output.
            return node.get_input_energy()

        return None

    def get_output_energy(
        self,
        node_id: EnergyUnitId,
    ) -> Energy | None:
        node = self.get_node(node_id)

        if not isinstance(node, Provider):
            return None

        output_energy = node.get_output_energy_type()(value=0)

        # A source node's output is the combined input demand of its successors.
        for successor_id in self._successors[node_id]:
            if len(self._predecessors[successor_id]) > 1:
                output_energy += self._allocate(successor_id)[node_id]
                continue

            successor_input_energy = self.get_input_energy(successor_id)
            if successor_input_energy is None:
                raise InvalidEnergyNetworkError(f"Energy unit {successor_id} has no input energy")

            output_energy += successor_input_energy

        return output_energy

    # Capacity and feasibility
    def get_capacity(
        self,
        unit_id: EnergyUnitId,
    ) -> Energy | None:
        unit = self.get_node(unit_id)

        if isinstance(unit, Provider):
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

        return output_energy > capacity

    def is_feasible(self) -> bool:
        return not any(self.is_capacity_exceeded(unit_id) for unit_id in self.get_topological_order())

    # Private topology construction and validation
    def _add_connections(
        self,
        connections: Iterable[EnergyConnection],
    ) -> None:
        for connection in connections:
            self._validate_connection(connection)

            self._successors[connection.source_id][connection.target_id] = None
            self._predecessors[connection.target_id][connection.source_id] = None

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
            if isinstance(unit, Consumer | DerivedInputProvider) and not self._predecessors[unit_id]:
                raise InvalidEnergyNetworkError(f"Energy unit {unit_id} requires input energy but has no predecessor")

    def _validate_predecessor_limits(self) -> None:
        for unit_id, unit in self._nodes.items():
            if not isinstance(unit, Junction):
                continue

            max_predecessors = unit.max_predecessors()
            predecessor_count = len(self._predecessors[unit_id])

            if max_predecessors is not None and predecessor_count > max_predecessors:
                raise InvalidEnergyNetworkError(
                    f"Energy unit {unit_id} allows at most {max_predecessors} predecessor(s), got {predecessor_count}"
                )

    def _validate_dispatch(self) -> None:
        for unit_id, predecessors in self._predecessors.items():
            if len(predecessors) <= 1:
                continue

            unit = self._nodes[unit_id]
            if not isinstance(unit, Junction):
                raise InvalidEnergyNetworkError(
                    f"Energy unit {unit_id} has {len(predecessors)} predecessors; only junctions support fan-in"
                )

            strategy = unit.get_dispatch_strategy()
            if strategy is None:
                raise EnergyAllocationRequiredError(
                    f"Junction {unit_id} has {len(predecessors)} predecessors and requires a dispatch strategy"
                )

            predecessor_ids = frozenset(predecessors)
            if strategy.get_provider_ids() != predecessor_ids:
                raise InvalidEnergyNetworkError(
                    f"Dispatch strategy provider IDs for junction {unit_id} must match its predecessors"
                )

            for predecessor_id in predecessors:
                successor_count = len(self._successors[predecessor_id])
                if successor_count != 1:
                    raise InvalidEnergyNetworkError(
                        f"Provider {predecessor_id} feeds dispatched junction {unit_id} and must have exactly "
                        f"one successor, got {successor_count}"
                    )

    def _allocate(self, junction_id: EnergyUnitId) -> dict[EnergyUnitId, Energy]:
        junction = self.get_node(junction_id)
        if not isinstance(junction, Junction):
            raise InvalidEnergyNetworkError(f"Energy unit {junction_id} requires dispatch but is not a junction")

        strategy = junction.get_dispatch_strategy()
        if strategy is None:
            raise EnergyAllocationRequiredError(f"Junction {junction_id} requires a dispatch strategy")

        demand = self.get_input_energy(junction_id)
        if demand is None:
            raise InvalidEnergyNetworkError(f"Junction {junction_id} has no input energy")

        candidates = tuple(
            ProviderAvailability(
                provider_id=predecessor_id,
                available=self._available_capacity(predecessor_id),
            )
            for predecessor_id in self._predecessors[junction_id]
        )
        return strategy.allocate(demand=demand, candidates=candidates)

    def _available_capacity(self, provider_id: EnergyUnitId) -> Energy | None:
        provider = self.get_node(provider_id)
        if not isinstance(provider, Provider):
            raise InvalidEnergyNetworkError(f"Energy unit {provider_id} is not a provider")

        return provider.capacity()

    @staticmethod
    def _get_output_type(
        node: EnergyNetworkNode,
    ) -> type[Energy]:
        if not isinstance(node, Provider):
            raise InvalidEnergyNetworkError(
                f"Source node of type '{type(node).__name__}' with id '{node.get_id()}' provides no energy"
            )

        return node.get_output_energy_type()

    @staticmethod
    def _get_input_type(
        node: EnergyNetworkNode,
    ) -> type[Energy]:
        if not isinstance(node, Consumer | DerivedInputProvider):
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
