from libecalc.domain.process.compressor.core.train.utils.common import (
    RECIRCULATION_BOUNDARY_TOLERANCE,
    calculate_outlet_pressure_and_stream,
)
from libecalc.domain.process.entities.shaft import Shaft
from libecalc.domain.process.process_solver.boundary import Boundary
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

    def get_speed_boundary(self) -> Boundary:
        """Min and max shaft speed from the compressor chart."""
        return Boundary(
            min=self.compressor_chart.minimum_speed,
            max=self.compressor_chart.maximum_speed,
        )

    def get_minimum_standard_rate(self, inlet_stream: FluidStream) -> float:
        """Minimum standard volumetric rate [sm³/day] at current speed.

        The inlet_stream should already be the stream entering the compressor
        (i.e., after any upstream conditioning units such as TemperatureSetter
        and LiquidRemover have processed it).
        """
        density = inlet_stream.density
        min_actual_rate = self.compressor_chart.minimum_rate_as_function_of_speed(self.speed)
        min_mass_rate_kg_per_h = min_actual_rate * density
        return self._fluid_service.mass_rate_to_standard_rate(
            fluid_model=inlet_stream.fluid_model,
            mass_rate_kg_per_h=min_mass_rate_kg_per_h,
        )

    def get_maximum_standard_rate(self, inlet_stream: FluidStream) -> float:
        """Maximum standard volumetric rate [sm³/day] at current speed."""
        density = inlet_stream.density
        max_actual_rate = self.compressor_chart.maximum_rate_as_function_of_speed(self.speed)
        max_mass_rate_kg_per_h = max_actual_rate * density
        return self._fluid_service.mass_rate_to_standard_rate(
            fluid_model=inlet_stream.fluid_model,
            mass_rate_kg_per_h=max_mass_rate_kg_per_h,
        )

    def get_recirculation_range(self, inlet_stream: FluidStream) -> Boundary:
        """How much recirculation (sm³/day) can be added while keeping the compressor within capacity.

        Returns:
            Boundary where:
                min = additional rate needed to reach the minimum operating point (surge limit)
                max = additional rate available before the maximum operating point is exceeded
        """
        min_rate = self.get_minimum_standard_rate(inlet_stream) * (1 + RECIRCULATION_BOUNDARY_TOLERANCE)
        max_rate = self.get_maximum_standard_rate(inlet_stream) * (1 - RECIRCULATION_BOUNDARY_TOLERANCE)
        return Boundary(
            min=max(0.0, min_rate - inlet_stream.standard_rate_sm3_per_day),
            max=max(0.0, max_rate - inlet_stream.standard_rate_sm3_per_day),
        )
