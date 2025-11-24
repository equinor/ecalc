from dataclasses import dataclass

from libecalc.domain.process.compressor.core.train.utils.common import calculate_outlet_pressure_and_stream
from libecalc.domain.process.value_objects.chart.chart import ChartData
from libecalc.domain.process.value_objects.chart.chart_area_flag import ChartAreaFlag
from libecalc.domain.process.value_objects.chart.compressor import CompressorChart
from libecalc.domain.process.value_objects.fluid_stream import FluidStream


@dataclass
class OperationalPoint:
    actual_rate_m3_per_h: float
    polytropic_head_joule_per_kg: float
    polytropic_efficiency: float
    is_valid: bool


class Compressor:
    def __init__(self, compressor_chart: ChartData):
        self._compressor_chart = CompressorChart(compressor_chart)

    @property
    def compressor_chart(self) -> CompressorChart:
        return self._compressor_chart

    def find_chart_area_flag_and_operational_point(
        self,
        speed: float,
        actual_rate_m3_per_h_including_asv: float,
        actual_rate_m3_per_h: float,
    ) -> tuple[ChartAreaFlag, OperationalPoint]:
        chart_result = self.compressor_chart.calculate_polytropic_head_and_efficiency_single_point(
            speed=speed,
            actual_rate_m3_per_hour_including_asv=actual_rate_m3_per_h_including_asv,
            actual_rate_m3_per_hour=actual_rate_m3_per_h,
        )
        operational_point = OperationalPoint(
            actual_rate_m3_per_h=actual_rate_m3_per_h,
            polytropic_head_joule_per_kg=chart_result.polytropic_head,
            polytropic_efficiency=chart_result.polytropic_efficiency,
            is_valid=chart_result.is_valid,
        )
        return chart_result.chart_area_flag, operational_point

    def compress(
        self,
        inlet_stream: FluidStream,
        polytropic_efficiency: float,
        polytropic_head_joule_per_kg: float,
    ) -> FluidStream:
        """
        Compresses the inlet fluid stream based on the provided polytropic efficiency and head.

        Args:
            inlet_stream (FluidStream): The incoming fluid stream to be compressed.
            polytropic_efficiency (float): The polytropic efficiency of the compressor.
            polytropic_head_joule_per_kg (float): The polytropic head in Joules per kilogram.

        Returns:
            FluidStream: The compressed fluid stream with updated pressure and temperature.
        """
        return calculate_outlet_pressure_and_stream(
            polytropic_efficiency=polytropic_efficiency,
            polytropic_head_joule_per_kg=polytropic_head_joule_per_kg,
            inlet_stream=inlet_stream,
        )
