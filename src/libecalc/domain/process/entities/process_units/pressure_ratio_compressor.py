from libecalc.common.chart_type import ChartType
from libecalc.domain.component_validation_error import (
    ProcessChartTypeValidationException,
)
from libecalc.domain.process.compressor.core.train.utils.enthalpy_calculations import (
    calculate_enthalpy_change_head_iteration,
)
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_system.process_unit import ProcessUnit, ProcessUnitId
from libecalc.domain.process.value_objects.chart.chart import ChartData
from libecalc.domain.process.value_objects.chart.compressor import CompressorChart
from libecalc.domain.process.value_objects.fluid_stream import FluidService, FluidStream
from libecalc.domain.process.value_objects.fluid_stream.fluid import Fluid

_ALLOWED_CHART_TYPES = (ChartType.GENERIC_FROM_INPUT, ChartType.GENERIC_FROM_DESIGN_POINT)


class PressureRatioCompressor(ProcessUnit):
    """Compressor stage that operates at a given pressure ratio.

    Provides the two methods CommonPressureRatioSolver needs:
      - propagate_stream_at_pressure_ratio()
      - get_recirculation_range_at_pressure_ratio()

    propagate_stream() raises NotImplementedError — a pressure ratio is always
    required to evaluate this unit.
    """

    def __init__(
        self,
        process_unit_id: ProcessUnitId,
        compressor_chart: ChartData,
        fluid_service: FluidService,
    ) -> None:
        if compressor_chart.origin_of_chart_data not in _ALLOWED_CHART_TYPES:
            raise ProcessChartTypeValidationException(
                f"PressureRatioCompressor requires a generic chart, "
                f"got {compressor_chart.origin_of_chart_data.value}."
            )
        self._id = process_unit_id
        self._compressor_chart = CompressorChart(compressor_chart)
        self._fluid_service = fluid_service

    def get_id(self) -> ProcessUnitId:
        return self._id

    def propagate_stream(self, inlet_stream: FluidStream) -> FluidStream:
        raise NotImplementedError(
            f"PressureRatioCompressor '{self._id}' cannot be propagated with propagate_stream(). "
            "Use propagate_stream_at_pressure_ratio() — a pressure ratio is always required."
        )

    @property
    def compressor_chart(self) -> CompressorChart:
        return self._compressor_chart

    def get_recirculation_range_at_pressure_ratio(self, inlet_stream: FluidStream, pressure_ratio: float) -> Boundary:
        """Surge and stonewall boundaries at the given pressure ratio.

        Uses head-based surge/stonewall limits — no shaft speed required.

        Returns:
            Boundary where:
                min = additional rate (sm³/day) needed to reach the surge line
                max = additional rate (sm³/day) available before stonewall
        """
        outlet_pressure = inlet_stream.pressure_bara * pressure_ratio
        enthalpy_change, polytropic_efficiency = calculate_enthalpy_change_head_iteration(
            outlet_pressure=outlet_pressure,
            polytropic_efficiency_vs_rate_and_head_function=self._compressor_chart.efficiency_as_function_of_rate_and_head,
            inlet_streams=inlet_stream,
            fluid_service=self._fluid_service,
        )
        head_joule_per_kg = float(enthalpy_change * polytropic_efficiency)

        min_actual_rate = float(self._compressor_chart.minimum_rate_as_function_of_head(head_joule_per_kg))
        max_actual_rate = float(self._compressor_chart.maximum_rate_as_function_of_head(head_joule_per_kg))

        density = inlet_stream.density
        min_sm3_per_day = self._fluid_service.mass_rate_to_standard_rate(
            fluid_model=inlet_stream.fluid_model,
            mass_rate_kg_per_h=min_actual_rate * density,
        )
        max_sm3_per_day = self._fluid_service.mass_rate_to_standard_rate(
            fluid_model=inlet_stream.fluid_model,
            mass_rate_kg_per_h=max_actual_rate * density,
        )
        inlet_sm3_per_day = inlet_stream.standard_rate_sm3_per_day
        return Boundary(
            min=max(0.0, min_sm3_per_day - inlet_sm3_per_day),
            max=max(0.0, max_sm3_per_day - inlet_sm3_per_day),
        )

    def propagate_stream_at_pressure_ratio(self, inlet_stream: FluidStream, pressure_ratio: float) -> FluidStream:
        """Propagate stream to an outlet pressure defined by a pressure ratio.

        The operating point is determined purely from inlet conditions and the
        target pressure ratio — no shaft speed required.

        Args:
            inlet_stream: The inlet fluid stream.
            pressure_ratio: Target outlet/inlet pressure ratio (e.g. 2.0 means double the pressure).

        Returns:
            The outlet FluidStream at target_pressure = inlet.pressure * pressure_ratio.
        """
        outlet_pressure = inlet_stream.pressure_bara * pressure_ratio
        enthalpy_change_joule_per_kg, polytropic_efficiency = calculate_enthalpy_change_head_iteration(
            outlet_pressure=outlet_pressure,
            polytropic_efficiency_vs_rate_and_head_function=self._compressor_chart.efficiency_as_function_of_rate_and_head,
            inlet_streams=inlet_stream,
            fluid_service=self._fluid_service,
        )
        target_enthalpy = float(inlet_stream.enthalpy_joule_per_kg + enthalpy_change_joule_per_kg)
        props = self._fluid_service.flash_ph(inlet_stream.fluid_model, float(outlet_pressure), target_enthalpy)
        outlet_fluid = Fluid(fluid_model=inlet_stream.fluid_model, properties=props)
        return inlet_stream.with_new_fluid(outlet_fluid)
