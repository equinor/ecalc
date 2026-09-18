from collections.abc import Mapping

from libecalc.energy import CapacityFailure, Energy, EnergyUnit, EnergyUnitId
from libecalc.energy.energy_network_topology import EnergyConnectionId, EnergyNetworkTopology


class EnergyNetwork:
    def __init__(
        self,
        topology: EnergyNetworkTopology,
        energy_units: Mapping[EnergyUnitId, EnergyUnit],
        connection_energy: dict[EnergyConnectionId, Energy],
    ):
        self._topology = topology
        self._energy_units = energy_units
        self._connection_energy = connection_energy

    def get_energy(self) -> dict[EnergyConnectionId, Energy]:
        return self._connection_energy

    def get_capacity_failures(self) -> dict[EnergyUnitId, CapacityFailure]:
        failures: dict[EnergyUnitId, CapacityFailure] = {}
        for energy_unit_id, energy_unit in self._energy_units.items():
            for failure in energy_unit.get_failures():
                if isinstance(failure, CapacityFailure):
                    failures[energy_unit_id] = failure
        return failures
