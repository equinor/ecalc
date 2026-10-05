from functools import cached_property

from libecalc.common.chart_type import ChartType
from libecalc.domain.process.value_objects.chart import ChartCurve
from libecalc.domain.process.value_objects.chart.chart import ChartData
from libecalc.domain.process.value_objects.chart.compressor.chart_creator import CompressorChartCreator
from libecalc.domain.process.value_objects.chart.compressor.operating_point_conversion import (
    rates_and_heads_from_operating_points,
)
from libecalc.domain.process.value_objects.chart.generic_from_design_point_chart_data import (
    GenericFromDesignPointChartData,
)
from libecalc.process.fluid_stream.fluid_model import FluidModel
from libecalc.process.fluid_stream.fluid_service import FluidService


class GenericFromInputChartData(ChartData):
    def __init__(
        self,
        fluid_model: FluidModel,
        fluid_service: FluidService,
        standard_rates: list[float],
        inlet_temperature: float,
        inlet_pressure: list[float],
        polytropic_efficiency: float,
        outlet_pressure: list[float],
    ):
        self._fluid_model = fluid_model
        self._fluid_service = fluid_service
        self._standard_rates = standard_rates
        self._inlet_pressure = inlet_pressure
        self._inlet_temperature = inlet_temperature
        self._polytropic_efficiency = polytropic_efficiency
        self._outlet_pressure = outlet_pressure

    @cached_property
    def _chart(self) -> GenericFromDesignPointChartData:
        converted = rates_and_heads_from_operating_points(
            fluid_model=self._fluid_model,
            fluid_service=self._fluid_service,
            standard_rates=self._standard_rates,
            inlet_temperature=self._inlet_temperature,
            inlet_pressure=self._inlet_pressure,
            outlet_pressure=self._outlet_pressure,
            polytropic_efficiency=self._polytropic_efficiency,
        )
        return CompressorChartCreator.from_rate_and_head_values(
            actual_volume_rates_m3_per_hour=converted.rates_m3_per_hour,
            heads_joule_per_kg=converted.heads_joule_per_kg,
            polytropic_efficiency=self._polytropic_efficiency,
        )

    def get_original_curves(self) -> list[ChartCurve]:
        return self._chart.get_original_curves()

    def get_adjusted_curves(self) -> list[ChartCurve]:
        return self.get_original_curves()  # No adjustment in generic charts

    @property
    def origin_of_chart_data(self) -> ChartType:
        return ChartType.GENERIC_FROM_INPUT

    @property
    def design_head(self):
        return self._chart.design_head

    @property
    def design_rate(self):
        return self._chart.design_rate
