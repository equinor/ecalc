from collections.abc import Mapping

from libecalc.common.ddd import value_object
from libecalc.energy.energy_failure import CapacityFailure
from libecalc.energy.energy_network_topology import EnergyConnectionId, EnergyNetworkTopology
from libecalc.energy.energy_types import Energy
from libecalc.energy.energy_unit import EnergyUnit, EnergyUnitId


@value_object
class EnergyNetwork:
    topology: EnergyNetworkTopology
    energy_units: tuple[EnergyUnit, ...]
    connection_demands: Mapping[EnergyConnectionId, Energy]
    capacities: Mapping[EnergyUnitId, Energy]
    connection_energy: Mapping[EnergyConnectionId, Energy]
    capacity_failures: Mapping[EnergyUnitId, CapacityFailure]

    def get_energy_units(self) -> tuple[EnergyUnit, ...]:
        return self.energy_units

    def is_feasible(self) -> bool:
        return not self.capacity_failures
