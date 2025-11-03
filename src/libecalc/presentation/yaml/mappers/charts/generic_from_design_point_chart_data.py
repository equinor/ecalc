from libecalc.common.serializable_chart import ChartCurveDTO, ChartDTO
from libecalc.domain.process.value_objects.chart import ChartCurve
from libecalc.domain.process.value_objects.chart.chart import ChartData


class GenericFromDesignPointChartData(ChartData):
    def __init__(self, curves: list[ChartCurve], design_head: float = None, design_rate: float = None):
        self._curves = curves
        self._design_head = design_head
        self._design_rate = design_rate

    def get_dto(self) -> ChartDTO:
        return ChartDTO(
            curves=[
                ChartCurveDTO(
                    speed_rpm=curve.speed,
                    rate_actual_m3_hour=curve.rate,
                    polytropic_head_joule_per_kg=curve.head,
                    efficiency_fraction=curve.efficiency,
                )
                for curve in self._curves
            ],
            design_rate=self._design_rate,
            design_head=self._design_head,
        )

    def get_curves(self) -> list[ChartCurve]:
        return self._curves
