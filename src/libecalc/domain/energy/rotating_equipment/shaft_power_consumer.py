from libecalc.domain.energy.rotating_equipment.rotating_equipment import RotatingEquipment


class ShaftPowerConsumer(RotatingEquipment):
    """Calculates shaft power from enthalpy rise across a process unit.

    P = mass_rate × (h_out − h_in)

    The outlet enthalpy already includes the effect of polytropic efficiency,
    since the process domain bakes it in during stream propagation.
    """

    def __init__(
        self,
        inlet_enthalpy_joule_per_kg: float,
        outlet_enthalpy_joule_per_kg: float,
        mass_rate_kg_per_h: float,
        source_id: str | None = None,
    ):
        self._inlet_enthalpy = inlet_enthalpy_joule_per_kg
        self._outlet_enthalpy = outlet_enthalpy_joule_per_kg
        self._mass_rate_kg_per_h = mass_rate_kg_per_h
        self._source_id = source_id

    def get_shaft_power_demand_mw(self) -> float:
        delta_enthalpy = self._outlet_enthalpy - self._inlet_enthalpy
        mass_rate_kg_per_s = self._mass_rate_kg_per_h / 3600
        return delta_enthalpy * mass_rate_kg_per_s / 1e6
