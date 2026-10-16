from libecalc.energy import Energy, EnergyUnitId, MechanicalPower
from libecalc.presentation.yaml.domain.energy import TimeSeriesEnergyUnit
from libecalc.process.shaft import Shaft


class TimeSeriesDriveTrain(TimeSeriesEnergyUnit):
    def __init__(
        self,
        *,
        name: str,
        shaft: Shaft,
        energy_unit_id: EnergyUnitId | None = None,
    ) -> None:
        super().__init__(name=name, energy_unit_id=energy_unit_id)
        self.shaft = shaft

    def get_shaft(self) -> Shaft:
        return self.shaft

    def get_input_energy_type(self) -> type[Energy]:
        return MechanicalPower
