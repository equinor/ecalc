from libecalc.energy.energy_failure import CapacityFailure, EnergyFailure
from libecalc.energy.energy_network_topology import EnergyConnectionId
from libecalc.energy.energy_types import Energy
from libecalc.energy.energy_unit import EnergyUnitId


class ConnectionPropagation:
    def __init__(
        self,
        energy: Energy,
        affected_by: tuple[EnergyFailure, ...],
    ) -> None:
        self.energy = energy
        self.affected_by = affected_by


class EnergyPropagation:
    def __init__(
        self,
        connections: dict[EnergyConnectionId, ConnectionPropagation],
        capacity_failures: dict[EnergyUnitId, CapacityFailure],
    ) -> None:
        self.connections = connections
        self.capacity_failures = capacity_failures
