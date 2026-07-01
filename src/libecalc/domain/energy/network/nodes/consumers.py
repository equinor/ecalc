from libecalc.domain.energy.network.energy_node import Consumer, EnergyNodeId, create_energy_node_id
from libecalc.domain.energy.network.energy_stream import EnergyStream


class RotatingEquipment(Consumer):
    """A single piece of rotating equipment as an energy node."""

    def __init__(self, demand: float):
        self._id = create_energy_node_id()
        self._demand = demand

    def get_id(self) -> EnergyNodeId:
        return self._id

    def get_demand(self) -> EnergyStream:
        return EnergyStream.mechanical(power_mw=self._demand)


class Shaft(Consumer):
    """
    Aggregates mechanical demand from rotating equipment on a common shaft,
    adjusted for mechanical losses (bearings, gearbox, friction).
    """

    def __init__(self, rotating_equipment: list[RotatingEquipment], mechanical_efficiency: float = 1.0):
        self._id = create_energy_node_id()
        self._rotating_equipment = rotating_equipment
        self._mechanical_efficiency = mechanical_efficiency

    def get_id(self) -> EnergyNodeId:
        return self._id

    def get_children(self) -> list[RotatingEquipment]:
        return self._rotating_equipment

    def get_demand(self) -> EnergyStream:
        demands = [eq.get_demand() for eq in self._rotating_equipment]
        if not demands:
            return EnergyStream.mechanical(0.0)

        expected_unit = demands[0].unit
        for d in demands[1:]:
            if d.unit != expected_unit:
                raise ValueError(f"Inconsistent units in rotating equipment demands: {d.unit} vs {expected_unit}")

        total = sum(d.value for d in demands)
        return EnergyStream.mechanical(total / self._mechanical_efficiency)
