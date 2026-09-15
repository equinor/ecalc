from libecalc.energy.energy_failure import CapacityFailure
from libecalc.energy.energy_network_topology import EnergyConnectionId
from libecalc.energy.energy_types import Energy
from libecalc.energy.energy_unit import EnergyUnitId


class EnergyPropagation:
    def __init__(
        self,
        connection_energy: dict[EnergyConnectionId, Energy],
        capacity_failures: dict[EnergyUnitId, CapacityFailure],
    ) -> None:
        self.connection_energy = connection_energy
        self.capacity_failures = capacity_failures
