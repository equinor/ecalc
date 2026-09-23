from libecalc.energy import CapacityFailure, Energy, EnergyUnitId
from libecalc.energy.energy_network_topology import EnergyConnectionId, EnergyNetworkTopology
from libecalc.energy.energy_unit_state import EnergyUnitState


class EnergyNetwork:
    """Snapshot of a calculated energy network, detached from energy units and factories."""

    def __init__(
        self,
        topology: EnergyNetworkTopology,
        unit_states: dict[EnergyUnitId, EnergyUnitState],
        connection_energy: dict[EnergyConnectionId, Energy],
    ):
        self._topology = topology
        self._unit_states = dict(unit_states)
        self._connection_energy = dict(connection_energy)

    def get_energy(self) -> dict[EnergyConnectionId, Energy]:
        return dict(self._connection_energy)

    def get_unit_states(self) -> dict[EnergyUnitId, EnergyUnitState]:
        return dict(self._unit_states)

    def get_unit_state(self, energy_unit_id: EnergyUnitId) -> EnergyUnitState:
        return self._unit_states[energy_unit_id]

    def get_capacity_failures(self) -> dict[EnergyUnitId, CapacityFailure]:
        failures: dict[EnergyUnitId, CapacityFailure] = {}
        for energy_unit_id, unit_state in self._unit_states.items():
            for failure in unit_state.failures:
                if isinstance(failure, CapacityFailure):
                    failures[energy_unit_id] = failure
        return failures

    def is_feasible(self) -> bool:
        return all(unit_state.is_feasible() for unit_state in self._unit_states.values())
