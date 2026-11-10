from libecalc.common.time_utils import Period
from libecalc.energy import EnergyUnitId
from libecalc.presentation.yaml.domain.energy import TimeSeriesEnergyUnit
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression
from libecalc.process.process_pipeline.process_unit import ProcessUnitId


class TimeSeriesProcessCompressor(TimeSeriesEnergyUnit):
    """
    A compressor solved by a process simulation, consuming shaft power from its drive train.

    Its gas power is only known once the process simulation has run, so the caller converts it to shaft power with
    `compressor_shaft_power` and the mechanical efficiency for the period.
    """

    def __init__(
        self,
        *,
        process_unit_id: ProcessUnitId,
        name: str,
        energy_unit_id: EnergyUnitId | None = None,
        mechanical_efficiency: TimeSeriesExpression | None = None,
    ) -> None:
        super().__init__(name=name, energy_unit_id=energy_unit_id)
        self.process_unit_id = process_unit_id
        self.mechanical_efficiency = mechanical_efficiency

    def get_mechanical_efficiency(self, period: Period) -> float:
        return self.mechanical_efficiency.get_value(period) if self.mechanical_efficiency is not None else 1.0
