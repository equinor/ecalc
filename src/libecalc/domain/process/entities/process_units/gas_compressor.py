from libecalc.domain.process.compressor.core.train.utils.common import calculate_outlet_pressure_and_stream
from libecalc.domain.process.entities.shaft import Shaft
from libecalc.domain.process.process_system.process_error import RateTooHighError, RateTooLowError
from libecalc.domain.process.process_system.process_unit import ProcessUnit, ProcessUnitId
from libecalc.domain.process.value_objects.chart.chart import ChartData
from libecalc.domain.process.value_objects.chart.compressor import CompressorChart
from libecalc.domain.process.value_objects.fluid_stream import FluidService, FluidStream


class GasCompressor(ProcessUnit):
    def __init__(
        self,
        process_unit_id: ProcessUnitId,
        compressor_chart: ChartData,
        fluid_service: FluidService,
        shaft: Shaft,
    ):
        self._id = process_unit_id
        self._compressor_chart = CompressorChart(compressor_chart)
        self._fluid_service = fluid_service
        self._shaft = shaft

    def get_id(self) -> ProcessUnitId:
        return self._id

    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream:
        actual_rate = inlet_stream.volumetric_rate_m3_per_hour
        if actual_rate < self.minimum_flow_rate:
            raise RateTooLowError()
        if actual_rate > self.maximum_flow_rate:
            raise RateTooHighError()

        chart_curve_at_given_speed = self.compressor_chart.get_curve_by_speed(speed=self.speed)
        if chart_curve_at_given_speed is not None:
            polytropic_head = float(chart_curve_at_given_speed.head_as_function_of_rate(actual_rate))
            polytropic_efficiency = float(chart_curve_at_given_speed.efficiency_as_function_of_rate(actual_rate))
        else:
            (
                polytropic_head,
                polytropic_efficiency,
            ) = self.compressor_chart.calculate_head_and_efficiency_for_internal_point_between_given_speeds(
                speed=self.speed,
                rate=actual_rate,
            )

        return calculate_outlet_pressure_and_stream(
            polytropic_efficiency=polytropic_efficiency,
            polytropic_head_joule_per_kg=polytropic_head,
            inlet_stream=inlet_stream,
            fluid_service=self._fluid_service,
        )

    @property
    def compressor_chart(self) -> CompressorChart:
        return self._compressor_chart

    @property
    def shaft(self) -> Shaft:
        return self._shaft

    @property
    def speed(self) -> float:
        return self.shaft.get_speed()

    @property
    def minimum_flow_rate(self) -> float:
        """Minimum flow rate in m3/h, as a function of speed if speed is set, otherwise the minimum flow rate at minimum speed."""
        if self.speed is None:
            return self.compressor_chart.minimum_rate
        return self.compressor_chart.minimum_rate_as_function_of_speed(self.speed)

    @property
    def maximum_flow_rate(self) -> float:
        """Maximum flow rate in m3/h, as a function of speed if speed is set, otherwise the maximum flow rate at maximum speed."""
        if self.speed is None:
            return self.compressor_chart.maximum_rate
        return self.compressor_chart.maximum_rate_as_function_of_speed(self.speed)
