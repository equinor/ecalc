from typing import Final, Self

from libecalc.common.ddd.entity import Entity
from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.ecalc_model.equipment.equipment_id import EquipmentId
from libecalc.ecalc_model.validation import InvalidEcalcModelException
from libecalc.process.chart.chart import Chart, ChartData
from libecalc.process.chart.compressor import CompressorChart
from libecalc.process.process_pipeline.process_unit import ProcessUnitId


class TimeSeriesProcessUnit(Entity[ProcessUnitId]):
    def __init__(self, *, process_unit_id: ProcessUnitId | None = None) -> None:
        self._id: Final[ProcessUnitId] = process_unit_id or self._create_id()

    def get_id(self) -> ProcessUnitId:
        return self._id

    @classmethod
    def _create_id(cls: type[Self]) -> ProcessUnitId:
        return ProcessUnitId(ecalc_id_generator())


class TimeSeriesCompressorProcessUnit(TimeSeriesProcessUnit):
    def __init__(
        self,
        *,
        compressor_chart: ChartData,
        compressor_equipment_id: EquipmentId,
        process_unit_id: ProcessUnitId | None = None,
    ) -> None:
        super().__init__(process_unit_id=process_unit_id)
        self._compressor_chart = CompressorChart(compressor_chart)
        self._compressor_equipment_id: Final[EquipmentId] = compressor_equipment_id

    @property
    def compressor_equipment_id(self) -> EquipmentId:
        return self._compressor_equipment_id

    @property
    def compressor_chart(self) -> CompressorChart:
        return self._compressor_chart


class TimeSeriesPumpProcessUnit(TimeSeriesProcessUnit):
    def __init__(
        self,
        *,
        pump_chart: ChartData,
        pump_equipment_id: EquipmentId,
        minimum_flow_rate_m3_per_hour: float | None = None,
        process_unit_id: ProcessUnitId | None = None,
    ) -> None:
        TimeSeriesPumpProcessUnit._validate(pump_chart, minimum_flow_rate_m3_per_hour)
        super().__init__(process_unit_id=process_unit_id)
        self._pump_chart: Final[ChartData] = pump_chart
        self._pump_equipment_id: Final[EquipmentId] = pump_equipment_id
        self._minimum_flow_rate_m3_per_hour: Final[float | None] = minimum_flow_rate_m3_per_hour

    @staticmethod
    def _validate(pump_chart: ChartData, minimum_flow_rate_m3_per_hour: float | None) -> None:
        chart = Chart(pump_chart)
        if any(not efficiency > 0 for curve in chart.curves for efficiency in curve.efficiency):
            raise InvalidEcalcModelException("Pump chart efficiency must be greater than 0.")
        if minimum_flow_rate_m3_per_hour is not None and not minimum_flow_rate_m3_per_hour >= chart.minimum_rate:
            raise InvalidEcalcModelException(
                f"Pump minimum flow rate ({minimum_flow_rate_m3_per_hour} m3/h) cannot be below the chart's minimum "
                f"rate ({chart.minimum_rate} m3/h)."
            )

    @property
    def pump_equipment_id(self) -> EquipmentId:
        return self._pump_equipment_id

    @property
    def pump_chart(self) -> ChartData:
        return self._pump_chart

    @property
    def minimum_flow_rate_m3_per_hour(self) -> float | None:
        return self._minimum_flow_rate_m3_per_hour


class TimeSeriesChokeProcessUnit(TimeSeriesProcessUnit):
    pass


class TimeSeriesDirectMixerProcessUnit(TimeSeriesProcessUnit):
    pass


class TimeSeriesDirectSplitterProcessUnit(TimeSeriesProcessUnit):
    pass


class TimeSeriesInletProcessUnit(TimeSeriesProcessUnit):
    pass


class TimeSeriesOutletProcessUnit(TimeSeriesProcessUnit):
    pass


class TimeSeriesLiquidRemoverProcessUnit(TimeSeriesProcessUnit):
    pass


class TimeSeriesMixerProcessUnit(TimeSeriesProcessUnit):
    pass


class TimeSeriesPressureDropperProcessUnit(TimeSeriesProcessUnit):
    pass


class TimeSeriesSplitterProcessUnit(TimeSeriesProcessUnit):
    pass


class TimeSeriesTemperatureSetterProcessUnit(TimeSeriesProcessUnit):
    pass
