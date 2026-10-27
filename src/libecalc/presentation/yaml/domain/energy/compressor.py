from libecalc.energy import EnergyUnitId
from libecalc.presentation.yaml.domain.energy import TimeSeriesEnergyUnit
from libecalc.process.process_pipeline.process_unit import ProcessUnitId


class TimeSeriesProcessCompressor(TimeSeriesEnergyUnit):
    def __init__(
        self,
        *,
        process_unit_id: ProcessUnitId,
        name: str,
        energy_unit_id: EnergyUnitId | None = None,
    ) -> None:
        super().__init__(name=name, energy_unit_id=energy_unit_id)
        self.process_unit_id = process_unit_id
