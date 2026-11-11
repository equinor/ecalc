from typing import Final, Self

from libecalc.common.ddd.entity import Entity
from libecalc.common.utils.ecalc_uuid import ecalc_id_generator
from libecalc.process.chart.chart import ChartData
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
    def __init__(self, *, compressor_chart: ChartData, process_unit_id: ProcessUnitId | None = None) -> None:
        super().__init__(process_unit_id=process_unit_id)
        self._compressor_chart = CompressorChart(compressor_chart)

    @property
    def compressor_chart(self) -> CompressorChart:
        return self._compressor_chart


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
