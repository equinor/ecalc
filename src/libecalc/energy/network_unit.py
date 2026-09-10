from libecalc.energy.energy_types import Energy
from libecalc.energy.energy_unit import EnergyUnit, EnergyUnitId


class EnergyNetworkUnit(EnergyUnit):
    """Topology representation of an energy unit, without operational behaviour."""

    def __init__(
        self,
        name: str,
        input_energy_type: type[Energy] | None,
        output_energy_type: type[Energy] | None,
        energy_unit_id: EnergyUnitId | None = None,
    ) -> None:
        super().__init__(name=name, energy_unit_id=energy_unit_id)
        self._input_energy_type = input_energy_type
        self._output_energy_type = output_energy_type

    def get_input_energy_type(self) -> type[Energy] | None:
        return self._input_energy_type

    def get_output_energy_type(self) -> type[Energy] | None:
        return self._output_energy_type
