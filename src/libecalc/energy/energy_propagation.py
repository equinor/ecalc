from libecalc.energy.energy_failure import CapacityFailure, EnergyFailure
from libecalc.energy.energy_network_topology import EnergyConnectionId
from libecalc.energy.energy_types import Energy
from libecalc.energy.energy_unit import EnergyUnitId


class ConnectionPropagation:
    def __init__(
        self,
        energy: Energy,
        ancestor_failures: tuple[EnergyFailure, ...],
        descendant_failures: tuple[EnergyFailure, ...],
    ) -> None:
        self.energy = energy
        self.ancestor_failures = ancestor_failures
        self.descendant_failures = descendant_failures


class EnergyPropagation:
    def __init__(
        self,
        connections: dict[EnergyConnectionId, ConnectionPropagation],
        capacity_failures: dict[EnergyUnitId, CapacityFailure],
    ) -> None:
        self.connections = connections
        self.capacity_failures = capacity_failures
