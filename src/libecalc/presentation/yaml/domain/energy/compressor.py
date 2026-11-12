from libecalc.common.time_utils import Period
from libecalc.ecalc_model.equipment.equipment_id import EquipmentId
from libecalc.energy import EnergyUnitId
from libecalc.presentation.yaml.domain.energy import TimeSeriesEnergyUnit
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


class TimeSeriesProcessCompressor(TimeSeriesEnergyUnit):
    """
    A compressor solved by a process simulation, consuming shaft power from its drive train.

    Its gas power is only known once the process simulation has run, so the caller converts it to shaft power with
    `compressor_shaft_power` and the mechanical efficiency for the period.
    """

    def __init__(
        self,
        *,
        compressor_equipment_id: EquipmentId,
        name: str,
        energy_unit_id: EnergyUnitId | None = None,
        mechanical_efficiency: TimeSeriesExpression | None = None,
    ) -> None:
        super().__init__(name=name, energy_unit_id=energy_unit_id)
        self.compressor_equipment_id = compressor_equipment_id
        self.mechanical_efficiency = mechanical_efficiency

    def get_mechanical_efficiency(self, period: Period) -> float:
        return self.mechanical_efficiency.get_value(period) if self.mechanical_efficiency is not None else 1.0
