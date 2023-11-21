from __future__ import annotations

import math
from enum import Enum
from math import isnan
from typing import Dict, List, Optional, Union

import numpy as np

from libecalc import dto
from libecalc.common.list.list_utils import elementwise_sum
from libecalc.common.logger import logger
from libecalc.common.units import Unit
from libecalc.core.models.results.base import (
    EnergyFunctionResult,
    EnergyModelBaseResult,
)
from libecalc.core.models.results.turbine import TurbineResult
from libecalc.dto.models import SingleSpeedChart, VariableSpeedChart


class CompressorTrainCommonShaftFailureStatus(str, Enum):
    TARGET_DISCHARGE_PRESSURE_TOO_HIGH = "TARGET_DISCHARGE_PRESSURE_TOO_HIGH"
    TARGET_DISCHARGE_PRESSURE_TOO_LOW = "TARGET_DISCHARGE_PRESSURE_TOO_LOW"
    SUCTION_PRESSURE_TOO_LOW = "SUCTION_PRESSURE_TOO_LOW"
    ABOVE_MAXIMUM_FLOW_RATE = "ABOVE_MAXIMUM_FLOW_RATE"
    BELOW_MINIMUM_FLOW_RATE = "BELOW_MINIMUM_FLOW_RATE"
    ABOVE_MAXIMUM_POWER = "ABOVE_MAXIMUM_POWER"
    INVALID_RATE_INPUT = "INVALID_RATE_INPUT"
    INVALID_SUCTION_PRESSURE_INPUT = "INVALID_SUCTION_PRESSURE_INPUT"
    INVALID_INTERMEDIATE_PRESSURE_INPUT = "INVALID_INTERMEDIATE_PRESSURE_INPUT"
    INVALID_DISCHARGE_PRESSURE_INPUT = "INVALID_DISCHARGE_PRESSURE_INPUT"
    NOT_CALCULATED = "NOT_CALCULATED"


class CompressorStreamCondition(EnergyModelBaseResult):
    pressure: Optional[List[Optional[float]]] = None
    pressure_before_choking: Optional[List[Optional[float]]] = None
    actual_rate_m3_per_hr: Optional[List[Optional[float]]] = None
    actual_rate_before_asv_m3_per_hr: Optional[List[Optional[float]]] = None
    density_kg_per_m3: Optional[List[Optional[float]]] = None
    kappa: Optional[List[Optional[float]]] = None
    z: Optional[List[Optional[float]]] = None
    temperature_kelvin: Optional[List[Optional[float]]] = None

    @classmethod
    def create_empty(cls, number_of_timesteps) -> CompressorStreamCondition:
        nans = [np.nan] * number_of_timesteps
        return cls(
            pressure=nans,
            pressure_before_choking=nans,
            actual_rate_m3_per_hr=nans,
            actual_rate_before_asv_m3_per_hr=nans,
            density_kg_per_m3=nans,
            kappa=nans,
            z=nans,
            temperature_kelvin=nans,
        )


class CompressorStageResult(EnergyModelBaseResult):
    energy_usage: List[Optional[float]]
    energy_usage_unit: Unit
    power: Optional[List[Optional[float]]] = None
    power_unit: Optional[Unit] = None

    mass_rate_kg_per_hr: Optional[
        List[Optional[float]]
    ] = None  # The gross mass rate passing through a compressor stage
    mass_rate_before_asv_kg_per_hr: Optional[
        List[Optional[float]]
    ] = None  # The net mass rate through a compressor stage

    inlet_stream_condition: CompressorStreamCondition
    outlet_stream_condition: CompressorStreamCondition

    polytropic_enthalpy_change_kJ_per_kg: Optional[List[Optional[float]]] = None
    polytropic_head_kJ_per_kg: Optional[List[Optional[float]]] = None
    polytropic_efficiency: Optional[List[Optional[float]]] = None
    polytropic_enthalpy_change_before_choke_kJ_per_kg: Optional[List[Optional[float]]] = None

    speed: Optional[List[Optional[float]]] = None
    asv_recirculation_loss_mw: List[Optional[float]]
    fluid_composition: Dict[str, Optional[float]]

    # Validity flags
    is_valid: List[bool]
    chart_area_flags: List[str]
    rate_has_recirculation: List[bool]
    rate_exceeds_maximum: List[bool]
    pressure_is_choked: List[bool]
    head_exceeds_maximum: List[bool]

    chart: Optional[Union[SingleSpeedChart, VariableSpeedChart]] = None

    @classmethod
    def create_empty(cls, number_of_timesteps: int) -> CompressorStageResult:
        """Create empty CompressorStageResult"""
        nans = [np.nan] * number_of_timesteps
        return cls(
            energy_usage=nans,
            energy_usage_unit=Unit.NONE,
            power=nans,
            power_unit=Unit.MEGA_WATT,
            mass_rate_kg_per_hr=nans,
            mass_rate_before_asv_kg_per_hr=nans,
            inlet_stream_condition=CompressorStreamCondition.create_empty(number_of_timesteps=number_of_timesteps),
            outlet_stream_condition=CompressorStreamCondition.create_empty(number_of_timesteps=number_of_timesteps),
            polytropic_enthalpy_change_kJ_per_kg=nans,
            polytropic_head_kJ_per_kg=nans,
            polytropic_efficiency=nans,
            polytropic_enthalpy_change_before_choke_kJ_per_kg=nans,
            speed=nans,
            asv_recirculation_loss_mw=nans,
            fluid_composition={},
            is_valid=[True] * number_of_timesteps,
            chart_area_flags=[dto.types.ChartAreaFlag.NOT_CALCULATED] * number_of_timesteps,
            rate_has_recirculation=[False] * number_of_timesteps,
            rate_exceeds_maximum=[False] * number_of_timesteps,
            pressure_is_choked=[False] * number_of_timesteps,
            head_exceeds_maximum=[False] * number_of_timesteps,
            chart=None,
        )


class CompressorTrainResult(EnergyFunctionResult):
    """The compressor train result component."""

    rate_sm3_day: Union[List[Optional[float]], List[List[Optional[float]]]]
    max_standard_rate: Optional[Union[List[Optional[float]], List[List[Optional[float]]]]] = None

    stage_results: List[CompressorStageResult]
    failure_status: List[Optional[CompressorTrainCommonShaftFailureStatus]]
    turbine_result: Optional[TurbineResult] = None

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
            elif isinstance(values, (Enum, str)):
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
    def rate(self) -> List[Optional[float]]:
        return self.rate_sm3_day

    @property
    def is_valid(self) -> List[bool]:
        """The sampled compressor model behaves "normally" and returns NaN-values when invalid.
        The turbine model can still be invalid if the sampled compressor model is valid (too high load),
        so need to check that as well.

        Note: We need to ensure all vectors are
        """
        failure_status_are_valid = (
            [t is None for t in self.failure_status]
            if self.failure_status is not None
            else [True] * len(self.energy_usage)
        )
        turbine_are_valid = (
            self.turbine_result.is_valid if self.turbine_result is not None else [True] * len(self.energy_usage)
        )

        stage_results_are_valid = (
            np.alltrue([stage.is_valid for stage in self.stage_results], axis=0)
            if self.stage_results is not None
            else [not isnan(x) for x in self.energy_usage]
        )
        return list(np.alltrue([failure_status_are_valid, turbine_are_valid, stage_results_are_valid], axis=0))

    @property
    def inlet_stream(self) -> CompressorStreamCondition:
        return self.stage_results[0].inlet_stream_condition

    @property
    def outlet_stream(self) -> CompressorStreamCondition:
        return self.stage_results[-1].outlet_stream_condition

    @property
    def mass_rate_kg_per_hr(self) -> List[float]:
        """Returns: The net mass rate that enters the compressor train at the first stage."""
        return self.stage_results[0].mass_rate_before_asv_kg_per_hr

    @property
    def pressure_is_choked(self) -> List[bool]:
        return list(np.any([stage.pressure_is_choked for stage in self.stage_results], axis=0))

    @property
    def recirculation_loss(self) -> List[float]:
        return list(elementwise_sum(*[stage.asv_recirculation_loss_mw for stage in self.stage_results]))

    @property
    def rate_exceeds_maximum(self) -> List[bool]:
        return list(np.any([stage.rate_exceeds_maximum for stage in self.stage_results], axis=0))

    @property
    def outlet_pressure_before_choking(self) -> Optional[List[float]]:
        return (
            [
                pressure if pressure is not None else math.nan
                for pressure in self.stage_results[-1].outlet_stream_condition.pressure_before_choking
            ]
            if self.stage_results[-1].outlet_stream_condition.pressure_before_choking is not None
            else None
        )
