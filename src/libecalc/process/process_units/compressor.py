from typing import Final

from libecalc.domain.process.compressor.core.train.utils.common import (
    RECIRCULATION_BOUNDARY_TOLERANCE,
    calculate_outlet_pressure_and_stream,
)
from libecalc.domain.process.value_objects.chart.chart import ChartData
from libecalc.domain.process.value_objects.chart.compressor import CompressorChart
from libecalc.process.fluid_stream.fluid_service import FluidService
from libecalc.process.fluid_stream.fluid_stream import FluidStream
from libecalc.process.process_pipeline.process_error import RateTooHighError, RateTooLowError
from libecalc.process.process_pipeline.process_unit import ProcessUnit, ProcessUnitId
from libecalc.process.process_solver.boundary import Boundary


class Compressor(ProcessUnit):
    def __init__(
        self,
        compressor_chart: ChartData,
        fluid_service: FluidService,
        process_unit_id: ProcessUnitId | None = None,
    ):
        self._id: Final[ProcessUnitId] = process_unit_id or ProcessUnit._create_id()
        self._compressor_chart = CompressorChart(compressor_chart)
        self._fluid_service = fluid_service
        self._speed: float | None = None
        self._polytropic_head_joule_per_kg: float | None = None
        self._polytropic_efficiency: float | None = None
        self._enthalpy_change_joule_per_kg: float | None = None
        self._power_megawatt: float | None = None
        self._actual_rate_m3_per_hour: float | None = None

    def get_id(self) -> ProcessUnitId:
        return self._id

    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream:
        actual_rate = inlet_stream.volumetric_rate_m3_per_hour
        if actual_rate < self.minimum_flow_rate:
            raise RateTooLowError(
                actual_rate=actual_rate,
                boundary_rate=self.minimum_flow_rate,
                process_unit_id=self._id,
            )
        if actual_rate > self.maximum_flow_rate:
            raise RateTooHighError(
                actual_rate=actual_rate,
                boundary_rate=self.maximum_flow_rate,
                process_unit_id=self._id,
            )

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

        self._polytropic_head_joule_per_kg = polytropic_head
        self._polytropic_efficiency = polytropic_efficiency
        self._actual_rate_m3_per_hour = actual_rate

        outlet_stream = calculate_outlet_pressure_and_stream(
            polytropic_efficiency=polytropic_efficiency,
            polytropic_head_joule_per_kg=polytropic_head,
            inlet_stream=inlet_stream,
            fluid_service=self._fluid_service,
        )
        enthalpy_change = polytropic_head / polytropic_efficiency
        self._enthalpy_change_joule_per_kg = enthalpy_change
        self._power_megawatt = enthalpy_change * inlet_stream.mass_rate_kg_per_h / 1e6 / 3600
        return outlet_stream

    @property
    def compressor_chart(self) -> CompressorChart:
        return self._compressor_chart

    @property
    def speed(self) -> float:
        if self._speed is None:
            raise ValueError("Speed not set. Compressor must be registered on a Shaft.")
        return self._speed

    @property
    def polytropic_head_joule_per_kg(self) -> float:
        if self._polytropic_head_joule_per_kg is None:
            raise ValueError("No propagation result. Call propagate_stream() first.")
        return self._polytropic_head_joule_per_kg

    @property
    def polytropic_efficiency(self) -> float:
        if self._polytropic_efficiency is None:
            raise ValueError("No propagation result. Call propagate_stream() first.")
        return self._polytropic_efficiency

    @property
    def enthalpy_change_joule_per_kg(self) -> float:
        if self._enthalpy_change_joule_per_kg is None:
            raise ValueError("No propagation result. Call propagate_stream() first.")
        return self._enthalpy_change_joule_per_kg

    @property
    def power_megawatt(self) -> float:
        """Power consumed by this compressor stage [MW]."""
        if self._power_megawatt is None:
            raise ValueError("No propagation result. Call propagate_stream() first.")
        return self._power_megawatt

    @property
    def actual_rate_m3_per_hour(self) -> float:
        """Volumetric rate at inlet conditions [m3/h]."""
        if self._actual_rate_m3_per_hour is None:
            raise ValueError("No propagation result. Call propagate_stream() first.")
        return self._actual_rate_m3_per_hour

    @property
    def minimum_flow_rate(self) -> float:
        """Minimum flow rate in m3/h, as a function of speed if speed is set, otherwise the minimum flow rate at minimum speed."""
        return self.compressor_chart.minimum_rate_as_function_of_speed(self.speed)

    @property
    def maximum_flow_rate(self) -> float:
        """Maximum flow rate in m3/h, as a function of speed if speed is set, otherwise the maximum flow rate at maximum speed."""
        return self.compressor_chart.maximum_rate_as_function_of_speed(self.speed)

    def set_speed(self, speed: float) -> None:
        """Set the rotational speed used for chart lookup."""
        self._speed = speed

    def get_minimum_standard_rate(self, inlet_stream: FluidStream) -> float:
        """Minimum standard volumetric rate [sm³/day] at current speed.

        The inlet_stream should already be the stream entering the compressor
        (i.e., after any upstream conditioning units such as TemperatureSetter
        and LiquidRemover have processed it).

        Note: since there is conversion between actual and standard rate, and numerical accuracy issues may later provide
        a RateTooHigh or RateTooLow error when it should not be there, we give the minimum rate a slight nudge upwards
        to make sure we stay inside capacity when we are supposed to stay inside capacity
        """
        density = inlet_stream.density
        min_actual_rate = self.compressor_chart.minimum_rate_as_function_of_speed(self.speed)
        min_mass_rate_kg_per_h = min_actual_rate * density
        return (
            self._fluid_service.mass_rate_to_standard_rate(
                fluid_model=inlet_stream.fluid_model,
                mass_rate_kg_per_h=min_mass_rate_kg_per_h,
            )
            + RECIRCULATION_BOUNDARY_TOLERANCE
        )

    def get_maximum_standard_rate(self, inlet_stream: FluidStream) -> float:
        """Maximum standard volumetric rate [sm³/day] at current speed.

        Note: since there is conversion between actual and standard rate, and numerical accuracy issues may later provide
        a RateTooHigh or RateTooLow error when it should not be there, we give the maximum rate a slight nudge downwards
        to make sure we stay inside capacity when we are supposed to stay inside capacity
        """
        density = inlet_stream.density
        max_actual_rate = self.compressor_chart.maximum_rate_as_function_of_speed(self.speed)
        max_mass_rate_kg_per_h = max_actual_rate * density
        return (
            self._fluid_service.mass_rate_to_standard_rate(
                fluid_model=inlet_stream.fluid_model,
                mass_rate_kg_per_h=max_mass_rate_kg_per_h,
            )
            - RECIRCULATION_BOUNDARY_TOLERANCE
        )

    def get_recirculation_range(self, inlet_stream: FluidStream) -> Boundary:
        """How much recirculation (sm³/day) can be added while keeping the compressor within capacity.

        Returns:
            Boundary where:
                min = additional rate needed to reach the minimum operating point (surge limit)
                max = additional rate available before the maximum operating point is exceeded
        """
        min_rate = self.get_minimum_standard_rate(inlet_stream)
        max_rate = self.get_maximum_standard_rate(inlet_stream)
        return Boundary(
            min=max(0.0, min_rate - inlet_stream.standard_rate_sm3_per_day),
            max=max(0.0, max_rate - inlet_stream.standard_rate_sm3_per_day),
        )
