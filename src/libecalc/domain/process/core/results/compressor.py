from __future__ import annotations

from collections.abc import Sequence
from enum import Enum
from math import isnan

import numpy as np

from libecalc.common.list.list_utils import elementwise_sum
from libecalc.common.units import Unit
from libecalc.domain.process.core.results.base import EnergyFunctionResult, EnergyResult, Quantity
from libecalc.domain.process.core.results.turbine import TurbineResult
from libecalc.domain.process.value_objects.chart.chart import ChartData
from libecalc.domain.process.value_objects.chart.chart_area_flag import ChartAreaFlag


class CompressorTrainCommonShaftFailureStatus(str, Enum):
    NO_FAILURE = "NO_FAILURE"
    TARGET_DISCHARGE_PRESSURE_TOO_HIGH = "TARGET_DISCHARGE_PRESSURE_TOO_HIGH"
    TARGET_DISCHARGE_PRESSURE_TOO_LOW = "TARGET_DISCHARGE_PRESSURE_TOO_LOW"
    TARGET_SUCTION_PRESSURE_TOO_HIGH = "TARGET_SUCTION_PRESSURE_TOO_HIGH"
    TARGET_SUCTION_PRESSURE_TOO_LOW = "TARGET_SUCTION_PRESSURE_TOO_LOW"
    TARGET_INTERMEDIATE_PRESSURE_TOO_HIGH = "TARGET_INTERMEDIATE_PRESSURE_TOO_HIGH"
    TARGET_INTERMEDIATE_PRESSURE_TOO_LOW = "TARGET_INTERMEDIATE_PRESSURE_TOO_LOW"
    ABOVE_MAXIMUM_FLOW_RATE = "ABOVE_MAXIMUM_FLOW_RATE"
    BELOW_MINIMUM_FLOW_RATE = "BELOW_MINIMUM_FLOW_RATE"
    ABOVE_MAXIMUM_POWER = "ABOVE_MAXIMUM_POWER"
    INVALID_RATE_INPUT = "INVALID_RATE_INPUT"
    INVALID_SUCTION_PRESSURE_INPUT = "INVALID_SUCTION_PRESSURE_INPUT"
    INVALID_INTERMEDIATE_PRESSURE_INPUT = "INVALID_INTERMEDIATE_PRESSURE_INPUT"
    INVALID_DISCHARGE_PRESSURE_INPUT = "INVALID_DISCHARGE_PRESSURE_INPUT"
    NOT_CALCULATED = "NOT_CALCULATED"


class TargetPressureStatus(str, Enum):
    NOT_CALCULATED = "NOT_CALCULATED"
    BELOW_TARGET_SUCTION_PRESSURE = "BELOW_TARGET_SUCTION_PRESSURE"
    ABOVE_TARGET_SUCTION_PRESSURE = "ABOVE_TARGET_SUCTION_PRESSURE"
    BELOW_TARGET_DISCHARGE_PRESSURE = "BELOW_TARGET_DISCHARGE_PRESSURE"
    ABOVE_TARGET_DISCHARGE_PRESSURE = "ABOVE_TARGET_DISCHARGE_PRESSURE"
    BELOW_TARGET_INTERMEDIATE_PRESSURE = "BELOW_TARGET_INTERMEDIATE_PRESSURE"
    ABOVE_TARGET_INTERMEDIATE_PRESSURE = "ABOVE_TARGET_INTERMEDIATE_PRESSURE"
    TARGET_PRESSURES_MET = "TARGET_PRESSURES_MET"


class CompressorStreamCondition:
    def __init__(
        self,
        pressure: list[float],
        actual_rate_m3_per_hr: list[float],
        actual_rate_before_asv_m3_per_hr: list[float],
        standard_rate_sm3_per_day: list[float],
        standard_rate_before_asv_sm3_per_day: list[float],
        density_kg_per_m3: list[float],
        kappa: list[float],
        z: list[float],
        temperature_kelvin: list[float],
    ):
        self.pressure = pressure
        self.actual_rate_m3_per_hr = actual_rate_m3_per_hr
        self.actual_rate_before_asv_m3_per_hr = actual_rate_before_asv_m3_per_hr
        self.standard_rate_sm3_per_day = standard_rate_sm3_per_day
        self.standard_rate_before_asv_sm3_per_day = standard_rate_before_asv_sm3_per_day
        self.density_kg_per_m3 = density_kg_per_m3
        self.kappa = kappa
        self.z = z
        self.temperature_kelvin = temperature_kelvin

    @classmethod
    def create_empty(cls, number_of_periods) -> CompressorStreamCondition:
        return cls(
            pressure=[np.nan] * number_of_periods,
            actual_rate_m3_per_hr=[np.nan] * number_of_periods,
            actual_rate_before_asv_m3_per_hr=[np.nan] * number_of_periods,
            standard_rate_sm3_per_day=[np.nan] * number_of_periods,
            standard_rate_before_asv_sm3_per_day=[np.nan] * number_of_periods,
            density_kg_per_m3=[np.nan] * number_of_periods,
            kappa=[np.nan] * number_of_periods,
            z=[np.nan] * number_of_periods,
            temperature_kelvin=[np.nan] * number_of_periods,
        )


class CompressorStageResult:
    def __init__(
        self,
        energy_usage: list[float],
        energy_usage_unit: Unit,
        power: list[float],
        power_unit: Unit,
        mass_rate_kg_per_hr: list[float],
        mass_rate_before_asv_kg_per_hr: list[float],
        inlet_stream_condition: CompressorStreamCondition,
        outlet_stream_condition: CompressorStreamCondition,
        polytropic_enthalpy_change_kJ_per_kg: list[float],
        polytropic_head_kJ_per_kg: list[float],
        polytropic_efficiency: list[float],
        polytropic_enthalpy_change_before_choke_kJ_per_kg: list[float],
        speed: list[float],
        asv_recirculation_loss_mw: list[float],
        fluid_composition: dict[str, float | None],
        is_valid: list[bool],
        chart_area_flags: list[str],
        rate_has_recirculation: list[bool],
        rate_exceeds_maximum: list[bool],
        pressure_is_choked: list[bool],
        head_exceeds_maximum: list[bool],
        chart: ChartData | None = None,
    ):
        assert chart is None or isinstance(chart, ChartData)
        self.energy_usage = energy_usage
        self.energy_usage_unit = energy_usage_unit
        self.power = power
        self.power_unit = power_unit

        self.mass_rate_kg_per_hr = mass_rate_kg_per_hr  # The gross mass rate passing through a compressor stage
        self.mass_rate_before_asv_kg_per_hr = (
            mass_rate_before_asv_kg_per_hr  # The net mass rate through a compressor stage
        )

        self.inlet_stream_condition = inlet_stream_condition
        self.outlet_stream_condition = outlet_stream_condition

        self.polytropic_enthalpy_change_kJ_per_kg = polytropic_enthalpy_change_kJ_per_kg
        self.polytropic_head_kJ_per_kg = polytropic_head_kJ_per_kg
        self.polytropic_efficiency = polytropic_efficiency
        self.polytropic_enthalpy_change_before_choke_kJ_per_kg = polytropic_enthalpy_change_before_choke_kJ_per_kg
        self.speed = speed
        self.asv_recirculation_loss_mw = asv_recirculation_loss_mw
        self.fluid_composition = fluid_composition

        # Validity flags
        self.is_valid = is_valid
        self.chart_area_flags = chart_area_flags
        self.rate_has_recirculation = rate_has_recirculation
        self.rate_exceeds_maximum = rate_exceeds_maximum
        self.pressure_is_choked = pressure_is_choked
        self.head_exceeds_maximum = head_exceeds_maximum
        self._chart = chart

    @property
    def chart(self) -> ChartData:
        return self._chart

    @chart.setter
    def chart(self, chart):
        assert chart is None or isinstance(chart, ChartData)
        self._chart = chart

    # Validate polytropic_efficiency, ensure list of floats and not arrays
    def __setattr__(self, name, value):
        if name == "polytropic_efficiency" and value is not None:
            value = [float(item) if isinstance(item, np.ndarray) and item.size == 1 else item for item in value]
        super().__setattr__(name, value)

    @classmethod
    def create_empty(cls, number_of_periods: int) -> CompressorStageResult:
        """Create empty CompressorStageResult"""

        def create_nans():
            return [np.nan] * number_of_periods

        return cls(
            energy_usage=create_nans(),
            energy_usage_unit=Unit.NONE,
            power=create_nans(),
            power_unit=Unit.MEGA_WATT,
            mass_rate_kg_per_hr=create_nans(),
            mass_rate_before_asv_kg_per_hr=create_nans(),
            inlet_stream_condition=CompressorStreamCondition.create_empty(number_of_periods=number_of_periods),
            outlet_stream_condition=CompressorStreamCondition.create_empty(number_of_periods=number_of_periods),
            polytropic_enthalpy_change_kJ_per_kg=create_nans(),
            polytropic_head_kJ_per_kg=create_nans(),
            polytropic_efficiency=create_nans(),
            polytropic_enthalpy_change_before_choke_kJ_per_kg=create_nans(),
            speed=create_nans(),
            asv_recirculation_loss_mw=create_nans(),
            fluid_composition={},
            is_valid=[True] * number_of_periods,
            chart_area_flags=[ChartAreaFlag.NOT_CALCULATED] * number_of_periods,
            rate_has_recirculation=[False] * number_of_periods,
            rate_exceeds_maximum=[False] * number_of_periods,
            pressure_is_choked=[False] * number_of_periods,
            head_exceeds_maximum=[False] * number_of_periods,
            chart=None,
        )


class CompressorTrainResult(EnergyFunctionResult):
    """The compressor train result component."""

    def __init__(
        self,
        rate_sm3_day: Sequence[float] | list[list[float]],
        max_standard_rate: Sequence[float] | None,
        inlet_stream_condition: CompressorStreamCondition,
        outlet_stream_condition: CompressorStreamCondition,
        stage_results: Sequence[CompressorStageResult],
        failure_status: Sequence[CompressorTrainCommonShaftFailureStatus | None],
        turbine_result: TurbineResult | None,
        energy_usage: list[float],
        energy_usage_unit: Unit,
        power: list[float] | None,
        power_unit: Unit | None,
    ):
        self.rate_sm3_day = rate_sm3_day
        self.max_standard_rate = max_standard_rate

        self.inlet_stream_condition = inlet_stream_condition
        self.outlet_stream_condition = outlet_stream_condition

        self.stage_results = stage_results
        self.failure_status = failure_status
        self._turbine_result = turbine_result
        self._energy_usage = Quantity(
            values=energy_usage,
            unit=energy_usage_unit,
        )

        if power is not None:
            assert power_unit is not None
            self._power = Quantity(
                values=power,
                unit=power_unit,
            )
        else:
            self._power = None

        self._requested_discharge_pressure = None
        self._requested_suction_pressure = None

    @property
    def rate(self) -> list[float]:
        return self.rate_sm3_day

    @property
    def turbine_result(self) -> TurbineResult:
        return self._turbine_result

    @turbine_result.setter
    def turbine_result(self, turbine_result: TurbineResult):
        turbine_energy_result = turbine_result.get_energy_result()
        self._power = turbine_energy_result.power
        self._energy_usage = turbine_energy_result.energy_usage
        self._turbine_result = turbine_result

    def get_energy_result(self) -> EnergyResult:
        return EnergyResult(
            energy_usage=self._energy_usage,
            power=self._power,
            is_valid=self._is_valid,
        )

    @property
    def _is_valid(self) -> list[bool]:
        """The sampled compressor model behaves "normally" and returns NaN-values when invalid.
        The turbine model can still be invalid if the sampled compressor model is valid (too high load),
        so need to check that as well.

        Note: We need to ensure all vectors are
        """
        failure_status_are_valid = [
            t is CompressorTrainCommonShaftFailureStatus.NO_FAILURE for t in self.failure_status
        ]

        turbine_are_valid = (
            self.turbine_result.get_energy_result().is_valid
            if self.turbine_result is not None
            else [True] * len(self._energy_usage)
        )

        stage_results_are_valid = (
            np.all([stage.is_valid for stage in self.stage_results], axis=0)
            if self.stage_results is not None
            else [not isnan(x) for x in self._energy_usage.values]
        )
        return np.all([failure_status_are_valid, turbine_are_valid, stage_results_are_valid], axis=0).tolist()

    @property
    def inlet_stream(self) -> CompressorStreamCondition:
        return self.inlet_stream_condition

    @property
    def outlet_stream(self) -> CompressorStreamCondition:
        return self.outlet_stream_condition

    @property
    def mass_rate_kg_per_hr(self) -> list[float]:
        """Returns: The net mass rate that enters the compressor train at the first stage."""
        return self.stage_results[0].mass_rate_before_asv_kg_per_hr

    @property
    def pressure_is_choked(self) -> list[bool]:
        return np.any([stage.pressure_is_choked for stage in self.stage_results], axis=0).tolist()

    @property
    def recirculation_loss(self) -> list[float]:
        return list(elementwise_sum(*[stage.asv_recirculation_loss_mw for stage in self.stage_results]))

    @property
    def rate_exceeds_maximum(self) -> list[bool]:
        return np.any([stage.rate_exceeds_maximum for stage in self.stage_results], axis=0).tolist()
