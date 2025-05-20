from __future__ import annotations

from collections.abc import Sequence
from enum import Enum
from math import isnan

import numpy as np

from libecalc.common.list.list_utils import elementwise_sum
from libecalc.common.logger import logger
from libecalc.common.serializable_chart import SingleSpeedChartDTO, VariableSpeedChartDTO
from libecalc.common.units import Unit
from libecalc.domain.process.chart.chart_area_flag import ChartAreaFlag
from libecalc.domain.process.core.results.base import (
    EnergyFunctionResult,
    EnergyModelBaseResult,
)
from libecalc.domain.process.core.results.turbine import TurbineResult


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


class CompressorStreamCondition(EnergyModelBaseResult):
    def __init__(
        self,
        pressure: Sequence[float | None] | None = None,
        actual_rate_m3_per_hr: Sequence[float | None] | None = None,
        actual_rate_before_asv_m3_per_hr: Sequence[float | None] | None = None,
        standard_rate_sm3_per_day: Sequence[float | None] | None = None,
        standard_rate_before_asv_sm3_per_day: Sequence[float | None] | None = None,
        density_kg_per_m3: Sequence[float | None] | None = None,
        kappa: Sequence[float | None] | None = None,
        z: Sequence[float | None] | None = None,
        temperature_kelvin: Sequence[float | None] | None = None,
    ):
        super().__init__()
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
        nans = [np.nan] * number_of_periods
        return cls(
            pressure=nans,
            actual_rate_m3_per_hr=nans,
            actual_rate_before_asv_m3_per_hr=nans,
            standard_rate_sm3_per_day=nans,
            standard_rate_before_asv_sm3_per_day=nans,
            density_kg_per_m3=nans,
            kappa=nans,
            z=nans,
            temperature_kelvin=nans,
        )


class CompressorStageResult(EnergyModelBaseResult):
    def __init__(
        self,
        energy_usage: Sequence[float | None],
        energy_usage_unit: Unit,
        power: Sequence[float | None] | None = None,
        power_unit: Unit | None = None,
        mass_rate_kg_per_hr: Sequence[float | None] | None = None,
        mass_rate_before_asv_kg_per_hr: Sequence[float | None] | None = None,
        inlet_stream_condition: CompressorStreamCondition = None,
        outlet_stream_condition: CompressorStreamCondition = None,
        polytropic_enthalpy_change_kJ_per_kg: Sequence[float | None] | None = None,
        polytropic_head_kJ_per_kg: Sequence[float | None] | None = None,
        polytropic_efficiency: Sequence[float | None] | None = None,
        polytropic_enthalpy_change_before_choke_kJ_per_kg: Sequence[float | None] | None = None,
        speed: Sequence[float | None] | None = None,
        asv_recirculation_loss_mw: Sequence[float | None] = None,
        fluid_composition: dict[str, float | None] = None,
        is_valid: Sequence[bool] = None,
        chart_area_flags: Sequence[str] = None,
        rate_has_recirculation: Sequence[bool] = None,
        rate_exceeds_maximum: Sequence[bool] = None,
        pressure_is_choked: Sequence[bool] = None,
        head_exceeds_maximum: Sequence[bool] = None,
        chart: SingleSpeedChartDTO | VariableSpeedChartDTO | None = None,
    ):
        super().__init__()
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
        self.chart = chart

    # Validate polytropic_efficiency, ensure list of floats and not arrays
    def __setattr__(self, name, value):
        if name == "polytropic_efficiency" and value is not None:
            value = [float(item) if isinstance(item, np.ndarray) and item.size == 1 else item for item in value]
        super().__setattr__(name, value)

    @classmethod
    def create_empty(cls, number_of_periods: int) -> CompressorStageResult:
        """Create empty CompressorStageResult"""
        nans = [np.nan] * number_of_periods
        return cls(
            energy_usage=nans,
            energy_usage_unit=Unit.NONE,
            power=nans,
            power_unit=Unit.MEGA_WATT,
            mass_rate_kg_per_hr=nans,
            mass_rate_before_asv_kg_per_hr=nans,
            inlet_stream_condition=CompressorStreamCondition.create_empty(number_of_periods=number_of_periods),
            outlet_stream_condition=CompressorStreamCondition.create_empty(number_of_periods=number_of_periods),
            polytropic_enthalpy_change_kJ_per_kg=nans,
            polytropic_head_kJ_per_kg=nans,
            polytropic_efficiency=nans,
            polytropic_enthalpy_change_before_choke_kJ_per_kg=nans,
            speed=nans,
            asv_recirculation_loss_mw=nans,
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
        rate_sm3_day: Sequence[float | None] | list[list[float | None]],
        max_standard_rate: Sequence[float | None] | list[list[float | None]] | None = None,
        inlet_stream_condition: CompressorStreamCondition = None,
        outlet_stream_condition: CompressorStreamCondition = None,
        stage_results: Sequence[CompressorStageResult] = None,
        failure_status: Sequence[CompressorTrainCommonShaftFailureStatus | None] = None,
        turbine_result: TurbineResult | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.rate_sm3_day = rate_sm3_day
        self.max_standard_rate = max_standard_rate

        self.inlet_stream_condition = inlet_stream_condition
        self.outlet_stream_condition = outlet_stream_condition

        self.stage_results = stage_results
        self.failure_status = failure_status
        self.turbine_result = turbine_result

    def extend(self, other: CompressorTrainResult) -> CompressorTrainResult:
        """This is used when merging different time slots when the energy function of a consumer changes over time.
        Append method covering all the basics. All additional extend methods needs to be covered in
        the _append-method.
        """
        initial_length = int(self.len)  # Used to fill in missing stage results in temporal models.

        def log_lost_result_data(attr: str) -> None:
            logger.warning(
                f"Concatenating two temporal compressor model results where attribute {attr} changes"
                f" over time. Only the first models value will be shown in the results."
            )

        for attribute, values in self.__dict__.items():
            other_values = other.__getattribute__(attribute)

            if values is None or other_values is None:
                continue
            elif isinstance(values, Enum | str):
                if values != other_values:
                    log_lost_result_data(attribute)
            elif attribute == "stage_results":
                # Padding with empty results if mismatching number of stages in temporal models.
                if len(values) > len(other_values):
                    for _ in range(len(values) - len(other_values)):
                        other_values.append(CompressorStageResult.create_empty(len(other.energy_usage)))
                elif len(values) < len(other_values):
                    for _ in range(len(other_values) - len(values)):
                        values.append(CompressorStageResult.create_empty(initial_length))
                # Appending compressor stage results. The number of stages should match.
                for i, stage_result in enumerate(values):
                    stage_result.extend(other_values[i])
            elif isinstance(values, EnergyModelBaseResult):
                # In case of nested models such as compressor with turbine
                values.extend(other_values)
            elif isinstance(values, list):
                # in case of list of lists
                if isinstance(values[0], list):
                    self.__setattr__(
                        attribute, [value + other_value for value, other_value in zip(values, other_values)]
                    )
                elif isinstance(other_values, list):
                    self.__setattr__(attribute, values + other_values)
                else:
                    self.__setattr__(attribute, values + [other_values])
            else:
                msg = (
                    f"{self.__repr_name__()} attribute {attribute} does not have an extend strategy."
                    f"Please contact eCalc support."
                )
                logger.warning(msg)
                raise NotImplementedError(msg)
        return self

    @property
    def rate(self) -> list[float | None]:
        return self.rate_sm3_day

    @property
    def is_valid(self) -> list[bool]:
        """The sampled compressor model behaves "normally" and returns NaN-values when invalid.
        The turbine model can still be invalid if the sampled compressor model is valid (too high load),
        so need to check that as well.

        Note: We need to ensure all vectors are
        """
        failure_status_are_valid = [
            t is CompressorTrainCommonShaftFailureStatus.NO_FAILURE for t in self.failure_status
        ]
        turbine_are_valid = (
            self.turbine_result.is_valid if self.turbine_result is not None else [True] * len(self.energy_usage)
        )

        stage_results_are_valid = (
            np.all([stage.is_valid for stage in self.stage_results], axis=0)
            if self.stage_results is not None
            else [not isnan(x) for x in self.energy_usage]
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
