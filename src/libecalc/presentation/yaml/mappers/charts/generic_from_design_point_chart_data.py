from libecalc.common.chart_type import ChartType
from libecalc.domain.process.value_objects.chart import ChartCurve
from libecalc.domain.process.value_objects.chart.chart import ChartData


class GenericFromDesignPointChartData(ChartData):
    def __init__(
        self,
        curves: list[ChartCurve],
        design_head: float = None,
        design_rate: float = None,
        origin_of_chart_data: ChartType = ChartType.GENERIC_FROM_DESIGN_POINT,
    ):
        self._curves = curves
        self._design_head = design_head
        self._design_rate = design_rate
        self._origin_of_chart_data = origin_of_chart_data

    @property
    def origin_of_chart_data(self) -> ChartType:
        return self._origin_of_chart_data

    @property
    def design_head(self):
        return self._design_head

    @property
    def design_rate(self):
        return self._design_rate

    def get_original_curves(self) -> list[ChartCurve]:
        return self._curves

    def get_adjusted_curves(self) -> list[ChartCurve]:
        return self.get_original_curves()  # No adjustment in generic charts
