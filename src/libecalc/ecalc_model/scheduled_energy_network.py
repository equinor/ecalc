from collections.abc import Mapping
from types import MappingProxyType

from libecalc.common.ddd import value_object
from libecalc.common.time_utils import Period
from libecalc.ecalc_model.input_schedule import InputSchedule
from libecalc.energy.energy_network_topology import EnergyNetworkTopology
from libecalc.energy.errors import InvalidEnergyNetworkError
from libecalc.energy.ids import EnergyUnitId


@value_object
class ScheduledEnergyNetwork:
    """A topology paired with the input schedule of every one of its exclusive-input nodes.

    Validated together so the two can never drift apart: schedule keys must exactly match the topology's
    exclusive-input nodes, and each schedule's candidates must exactly match that node's predecessors.
    """

    topology: EnergyNetworkTopology
    schedules: Mapping[EnergyUnitId, InputSchedule]

    def __post_init__(self) -> None:
        # A defensive, read-only copy: without it, the caller's own dict could still be mutated after
        # construction, silently invalidating what we just checked below.
        object.__setattr__(self, "schedules", MappingProxyType(dict(self.schedules)))
        exclusive_input_nodes = self.topology.get_exclusive_input_nodes()
        scheduled_nodes = frozenset(self.schedules.keys())

        missing_schedules = exclusive_input_nodes - scheduled_nodes
        if missing_schedules:
            raise InvalidEnergyNetworkError(f"Missing input schedules for energy units: {missing_schedules}")

        unexpected_schedules = scheduled_nodes - exclusive_input_nodes
        if unexpected_schedules:
            raise InvalidEnergyNetworkError(
                f"Input schedules for energy units that are not exclusive-input nodes: {unexpected_schedules}"
            )

        for node_id, schedule in self.schedules.items():
            predecessors = self.topology.get_predecessors(node_id)
            mismatched_candidates = schedule.get_candidate_ids() ^ predecessors
            if mismatched_candidates:
                raise InvalidEnergyNetworkError(
                    f"Input schedule for {node_id} does not exactly match its predecessors: {mismatched_candidates}"
                )

    def active_connections_at(self, period: Period) -> Mapping[EnergyUnitId, EnergyUnitId]:
        """Which predecessor is active, at `period`, for every exclusive-input node."""
        return {node_id: schedule.active_at(period) for node_id, schedule in self.schedules.items()}

    def __hash__(self) -> int:
        # A `Mapping` isn't hashable itself; hash its items instead, mirroring `__eq__`'s by-value semantics.
        return hash((self.topology, frozenset(self.schedules.items())))
