from libecalc.domain.process.value_objects.chart import ChartCurve
from libecalc.domain.process.value_objects.chart.chart import ChartData
from libecalc.domain.process.value_objects.chart.compressor.chart_creator import CompressorChartCreator
from libecalc.presentation.yaml.mappers.charts.user_defined_chart_data import UserDefinedChartData


class ChartDataFactory:
    @staticmethod
    def from_design_point(rate: float, head: float, efficiency: float) -> ChartData:
        return CompressorChartCreator.from_rate_and_head_design_point(
            design_actual_rate_m3_per_hour=rate,
            design_head_joule_per_kg=head,
            polytropic_efficiency=efficiency,
        )

    @staticmethod
    def from_rate_and_head(rate: list[float], head: list[float], efficiency: float) -> ChartData:
        return CompressorChartCreator.from_rate_and_head_values(
            actual_volume_rates_m3_per_hour=rate,
            heads_joule_per_kg=head,
            polytropic_efficiency=efficiency,
        )

    @staticmethod
    def from_curves(curves: list[ChartCurve], control_margin: float = 0.0) -> ChartData:
        return UserDefinedChartData(
            curves=curves,
            control_margin=control_margin,
        )
