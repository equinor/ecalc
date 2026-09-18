from libecalc.common.ddd import value_object
from libecalc.energy.energy_failure import CapacityFailure, EnergyFailureStatus
from libecalc.energy.energy_network_topology import EnergyConnectionId, EnergyNetworkTopology
from libecalc.energy.energy_types import Energy
from libecalc.energy.energy_unit import EnergyUnit, EnergyUnitId
from libecalc.energy.errors import InvalidEnergyNetworkError


@value_object
class EnergyNetwork:
    topology: EnergyNetworkTopology
    energy_units: tuple[EnergyUnit, ...]
    connection_demands: dict[EnergyConnectionId, Energy]
    capacities: dict[EnergyUnitId, Energy]
    connection_energy: dict[EnergyConnectionId, Energy]

    def get_energy_units(self) -> tuple[EnergyUnit, ...]:
        return self.energy_units

    def get_energy_unit(self, energy_unit_id: EnergyUnitId) -> EnergyUnit:
        for energy_unit in self.energy_units:
            if energy_unit.get_id() == energy_unit_id:
                return energy_unit
        raise KeyError(energy_unit_id)

    def get_connection_energy(self, connection_id: EnergyConnectionId) -> Energy:
        return self.connection_energy[connection_id]

    def get_consumer_demand(self, consumer_id: EnergyUnitId) -> Energy:
        for connection in self.topology.get_connections():
            if connection.target_id == consumer_id and connection.id in self.connection_demands:
                return self.connection_demands[connection.id]
        raise KeyError(f"No consumer demand found for energy unit ID: {consumer_id}")

    def get_capacity(self, energy_unit_id: EnergyUnitId) -> Energy | None:
        return self.capacities.get(energy_unit_id)

    def get_capacity_failure(self, energy_unit_id: EnergyUnitId) -> CapacityFailure | None:
        capacity = self.get_capacity(energy_unit_id)
        if capacity is None:
            return None

        required_energy = self._get_output_energy(energy_unit_id)
        if required_energy <= capacity:
            return None

        return CapacityFailure(
            status=EnergyFailureStatus.CAPACITY_EXCEEDED,
            required_energy=required_energy,
            capacity=capacity,
        )

    def get_capacity_failures(self) -> dict[EnergyUnitId, CapacityFailure]:
        failures: dict[EnergyUnitId, CapacityFailure] = {}
        for energy_unit_id in self.capacities:
            failure = self.get_capacity_failure(energy_unit_id)
            if failure is not None:
                failures[energy_unit_id] = failure
        return failures

    def is_feasible(self) -> bool:
        return not self.get_capacity_failures()

    def _get_output_energy(self, energy_unit_id: EnergyUnitId) -> Energy:
        energy_unit = self.get_energy_unit(energy_unit_id)
        output_energy_type = energy_unit.get_output_energy_type()
        if output_energy_type is None:
            raise InvalidEnergyNetworkError(
                f"Energy unit '{energy_unit.get_name()}' ({energy_unit_id}) has no output energy"
            )

        output_energy = output_energy_type(0)
        for successor_id in self.topology.get_successors(energy_unit_id):
            connection = self.topology.get_connection(energy_unit_id, successor_id)
            output_energy += self.get_connection_energy(connection.id)
        return output_energy
