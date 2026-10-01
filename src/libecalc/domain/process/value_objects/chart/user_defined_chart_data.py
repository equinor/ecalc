from functools import cached_property

from libecalc.common.chart_type import ChartType
from libecalc.domain.process.value_objects.chart import ChartCurve
from libecalc.domain.process.value_objects.chart.chart import ChartData


class UserDefinedChartData(ChartData):
    def __init__(self, curves: list[ChartCurve], control_margin: float | None):
        self._curves = sorted(curves, key=lambda x: x.speed)
        self._control_margin = control_margin  # TODO: Set to 0 if not set? Default: 0?
        self._origin_of_chart_data = ChartType.SINGLE_SPEED if len(curves) == 1 else ChartType.VARIABLE_SPEED

    @property
    def origin_of_chart_data(self) -> ChartType:
        return self._origin_of_chart_data

    @property
    def control_margin(self) -> float | None:
        return self._control_margin

    @cached_property
    def _adjusted_curves(self) -> list[ChartCurve]:
        return [curve.adjust_for_control_margin(self._control_margin) for curve in self._curves]

    @cached_property
    def _original_curves(self) -> list[ChartCurve]:
        return [curve.deep_copy() for curve in self._curves]

    def get_original_curves(self) -> list[ChartCurve]:
        return self._original_curves

    def get_adjusted_curves(self) -> list[ChartCurve]:
        return self._adjusted_curves
