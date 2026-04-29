from collections.abc import Sequence
from typing import Final

from libecalc.common.chart_type import ChartType
from libecalc.domain.component_validation_error import ComponentValidationException, ProcessChartTypeValidationException
from libecalc.domain.process.compressor.core.train.utils.enthalpy_calculations import (
    calculate_enthalpy_change_head_iteration,
)
from libecalc.domain.process.entities.process_units.choke import Choke
from libecalc.domain.process.entities.process_units.compressor import Compressor
from libecalc.domain.process.process_pipeline.process_pipeline import ProcessPipeline
from libecalc.domain.process.process_solver.boundary import Boundary
from libecalc.domain.process.process_solver.configuration import Configuration, ConfigurationHandlerId
from libecalc.domain.process.process_solver.float_constraint import FloatConstraint
from libecalc.domain.process.process_solver.solver import (
    Solution,
    SolverFailureStatus,
    TargetNotAchievableEvent,
)
from libecalc.domain.process.process_solver.solvers.recirculation_solver import RecirculationConfiguration
from libecalc.domain.process.value_objects.fluid_stream import FluidService, FluidStream
from libecalc.domain.process.value_objects.fluid_stream.fluid import Fluid

_ALLOWED_CHART_TYPES = (ChartType.GENERIC_FROM_INPUT, ChartType.GENERIC_FROM_DESIGN_POINT)


class EqualRatioOutletPressureCalculator:
    """Analytic outlet-pressure calculator: equal pressure ratio per stage, individual anti-surge."""

    def __init__(
        self,
        system: ProcessPipeline,
        fluid_service: FluidService,
    ) -> None:
        self._system: Final = system
        self._fluid_service: Final = fluid_service
        for unit in system.get_process_units():
            if isinstance(unit, Choke):
                raise ComponentValidationException(
                    f"EqualRatioOutletPressureCalculator does not support pressure-dropping units; "
                    f"found Choke {unit.get_id()} in the pipeline."
                )
            if isinstance(unit, Compressor):
                origin = unit.compressor_chart.chart_data.origin_of_chart_data
                if origin not in _ALLOWED_CHART_TYPES:
                    raise ProcessChartTypeValidationException(
                        f"EqualRatioOutletPressureCalculator requires a generic chart "
                        f"for compressor {unit.get_id()}; got {origin.value}."
                    )

    def _per_stage_pressure_ratio(
        self,
        pressure_constraint: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> float | None:
        n = sum(1 for u in self._system.get_process_units() if isinstance(u, Compressor))
        if n == 0:
            return None
        total_ratio = pressure_constraint.value / inlet_stream.pressure_bara
        if total_ratio <= 0:
            return None
        return total_ratio ** (1.0 / n)

    def _with_rate_delta(self, stream: FluidStream, delta: float) -> FluidStream:
        if delta == 0.0:
            return stream
        return self._fluid_service.create_stream_from_standard_rate(
            fluid_model=stream.fluid_model,
            pressure_bara=stream.pressure_bara,
            temperature_kelvin=stream.temperature_kelvin,
            standard_rate_m3_per_day=stream.standard_rate_sm3_per_day + delta,
        )

    def _evaluate_stage(
        self,
        compressor: Compressor,
        inlet_stream: FluidStream,
        pressure_ratio: float,
    ) -> tuple[Boundary, FluidStream]:
        chart = compressor.compressor_chart
        outlet_pressure = inlet_stream.pressure_bara * pressure_ratio
        enthalpy_change, polytropic_efficiency = calculate_enthalpy_change_head_iteration(
            outlet_pressure=outlet_pressure,
            polytropic_efficiency_vs_rate_and_head_function=chart.efficiency_as_function_of_rate_and_head,
            inlet_streams=inlet_stream,
            fluid_service=self._fluid_service,
        )
        head_joule_per_kg = float(enthalpy_change * polytropic_efficiency)

        min_actual_rate = float(chart.minimum_rate_as_function_of_head(head_joule_per_kg))
        max_actual_rate = float(chart.maximum_rate_as_function_of_head(head_joule_per_kg))
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
        recirc_range = Boundary(
            min=min_sm3_per_day - inlet_sm3_per_day,
            max=max_sm3_per_day - inlet_sm3_per_day,
        )

        target_enthalpy = float(inlet_stream.enthalpy_joule_per_kg + enthalpy_change)
        props = self._fluid_service.flash_ph(inlet_stream.fluid_model, float(outlet_pressure), target_enthalpy)
        outlet_fluid = Fluid(fluid_model=inlet_stream.fluid_model, properties=props)
        outlet_stream = inlet_stream.with_new_fluid(outlet_fluid)

        return recirc_range, outlet_stream

    def find_solution(
        self,
        pressure_constraint: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> Solution[Sequence[Configuration]]:
        pressure_ratio_per_stage = self._per_stage_pressure_ratio(pressure_constraint, inlet_stream)
        if pressure_ratio_per_stage is None:
            return Solution(
                success=False,
                configuration=[],
                failure_event=TargetNotAchievableEvent(
                    status=SolverFailureStatus.MAXIMUM_ACHIEVABLE_DISCHARGE_PRESSURE_BELOW_TARGET,
                    achievable_value=inlet_stream.pressure_bara,
                    target_value=pressure_constraint.value,
                    source_id=self._system.get_id(),
                ),
            )

        configurations: list[Configuration[RecirculationConfiguration]] = []
        current_inlet = inlet_stream

        for unit in self._system.get_process_units():
            if isinstance(unit, Compressor):
                recirc_range, _ = self._evaluate_stage(unit, current_inlet, pressure_ratio_per_stage)
                if recirc_range.max < 0.0:
                    return Solution(
                        success=False,
                        configuration=configurations,
                        failure_event=TargetNotAchievableEvent(
                            status=SolverFailureStatus.MAXIMUM_ACHIEVABLE_DISCHARGE_PRESSURE_BELOW_TARGET,
                            achievable_value=current_inlet.pressure_bara,
                            target_value=pressure_constraint.value,
                            source_id=self._system.get_id(),
                        ),
                    )
                # Individual anti-surge.
                recirculation_rate = max(0.0, recirc_range.min)

                configurations.append(
                    Configuration(
                        configuration_handler_id=ConfigurationHandlerId(unit.get_id()),
                        value=RecirculationConfiguration(recirculation_rate=recirculation_rate),
                    )
                )

                inner_inlet = self._with_rate_delta(current_inlet, recirculation_rate)
                _, outlet_with_recirc = self._evaluate_stage(unit, inner_inlet, pressure_ratio_per_stage)
                current_inlet = self._with_rate_delta(outlet_with_recirc, -recirculation_rate)
            else:
                current_inlet = unit.propagate_stream(current_inlet)

        return Solution(success=True, configuration=configurations)

    def get_max_standard_rate(
        self,
        pressure_constraint: FloatConstraint,
        inlet_stream: FluidStream,
    ) -> float:
        """Maximum inlet standard rate [sm³/day] meeting target pressure (bottleneck across stages)."""
        pressure_ratio_per_stage = self._per_stage_pressure_ratio(pressure_constraint, inlet_stream)
        if pressure_ratio_per_stage is None:
            return 0.0

        max_inlet_rate = float("inf")
        current_inlet = inlet_stream

        for unit in self._system.get_process_units():
            if isinstance(unit, Compressor):
                stage_inlet_rate = current_inlet.standard_rate_sm3_per_day
                recirc_range, current_inlet = self._evaluate_stage(unit, current_inlet, pressure_ratio_per_stage)
                stage_max = stage_inlet_rate + recirc_range.max
                max_inlet_rate = min(max_inlet_rate, stage_max)
            else:
                current_inlet = unit.propagate_stream(current_inlet)

        return max(0.0, max_inlet_rate)
