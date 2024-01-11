from __future__ import annotations

from typing import List, Optional, Union

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic_core.core_schema import ValidationInfo

from libecalc import dto
from libecalc.common.units import Unit
from libecalc.core.models.results.compressor import (
    CompressorStageResult,
    CompressorStreamCondition,
    CompressorTrainCommonShaftFailureStatus,
)
from libecalc.dto.types import ChartAreaFlag


class CompressorTrainStageResultSingleTimeStep(BaseModel):
    """One stage, one time step.

    Actual rate per hour [Am3/h]
    mass rate [kg/hour]
    head [J/kg]
    Polytropic efficiency (0, 1]
    power [MW]
    """

    inlet_stream: Optional[dto.FluidStream] = None
    outlet_stream: Optional[dto.FluidStream] = None

    # actual rate [Am3/hour] = mass rate [kg/hour] / density [kg/m3]
    inlet_actual_rate_m3_per_hour: float
    inlet_actual_rate_asv_corrected_m3_per_hour: float

    outlet_actual_rate_m3_per_hour: float
    outlet_actual_rate_asv_corrected_m3_per_hour: float

    mass_rate_kg_per_hour: float
    mass_rate_asv_corrected_kg_per_hour: float

    polytropic_head_kJ_per_kg: float
    polytropic_efficiency: float

    polytropic_enthalpy_change_kJ_per_kg: float
    polytropic_enthalpy_change_before_choke_kJ_per_kg: float
    power_megawatt: float

    chart_area_flag: ChartAreaFlag

    rate_has_recirculation: Optional[bool] = None
    rate_exceeds_maximum: Optional[bool] = None
    pressure_is_choked: Optional[bool] = None
    head_exceeds_maximum: Optional[bool] = None

    inlet_pressure_before_choking: float
    outlet_pressure_before_choking: float

    point_is_valid: bool
    model_config = ConfigDict(extra="forbid")

    @classmethod
    def create_empty(cls) -> CompressorTrainStageResultSingleTimeStep:
        return cls(
            inlet_stream=None,
            outlet_stream=None,
            # actual rate [Am3/hour] = mass rate [kg/hour] / density [kg/m3]
            inlet_actual_rate_m3_per_hour=0.0,
            inlet_actual_rate_asv_corrected_m3_per_hour=0.0,
            outlet_actual_rate_m3_per_hour=0.0,
            outlet_actual_rate_asv_corrected_m3_per_hour=0.0,
            mass_rate_kg_per_hour=0.0,
            mass_rate_asv_corrected_kg_per_hour=0.0,
            polytropic_head_kJ_per_kg=0.0,
            polytropic_efficiency=1.0,
            polytropic_enthalpy_change_kJ_per_kg=0.0,
            polytropic_enthalpy_change_before_choke_kJ_per_kg=0.0,
            power_megawatt=0.0,
            chart_area_flag=ChartAreaFlag.NOT_CALCULATED,
            rate_has_recirculation=False,
            rate_exceeds_maximum=False,
            pressure_is_choked=False,
            head_exceeds_maximum=False,
            inlet_pressure_before_choking=np.nan,
            outlet_pressure_before_choking=np.nan,
            point_is_valid=True,
        )

    @property
    def is_valid(self) -> bool:
        return self.chart_area_flag == ChartAreaFlag.INTERNAL_POINT or self.point_is_valid is True

    @property
    def discharge_pressure(self) -> float:
        return self.outlet_stream.pressure_bara

    @property
    def inlet_pressure(self) -> float:
        return self.inlet_stream.pressure_bara

    @property
    def asv_recirculation_loss_mw(self) -> float:
        """The loss of energy in MW because of ASV recirculation.
        :return:
        """
        asv_loss_kilo_joule_per_hour = (
            self.mass_rate_asv_corrected_kg_per_hour - self.mass_rate_kg_per_hour
        ) * self.polytropic_enthalpy_change_kJ_per_kg

        # Conversion J/s = W -> J/h = W / 3600 -> kJ/h = MW / 3600000
        kilo_joule_per_hour_to_mw_factor = 1 / (60 * 60 * 1000)

        return asv_loss_kilo_joule_per_hour * kilo_joule_per_hour_to_mw_factor


class CompressorTrainResultSingleTimeStep(BaseModel):
    """All stages, one time step.

    speed [rpm]
    pressure [bar]
    rate [Sm3/day]
    mass rate [kg/hour]
    """

    speed: float
    stage_results: List[CompressorTrainStageResultSingleTimeStep]

    # Used to override failure status is some cases.
    failure_status: Optional[CompressorTrainCommonShaftFailureStatus] = Field(default=None, validate_default=True)

    @staticmethod
    def from_result_list_to_dto(
        result_list: List[CompressorTrainResultSingleTimeStep],
        compressor_charts: Optional[List[Union[dto.SingleSpeedChart, dto.VariableSpeedChart]]],
    ) -> List[CompressorStageResult]:
        number_of_stages = max([len(t.stage_results) for t in result_list])

        # Create empty compressor stage results and inlet/outlet stream conditions. This is to ensure correct
        # number of values and timesteps in case of None etc.
        compressor_stage_result = [
            CompressorStageResult.create_empty(len(result_list)) for i in range(number_of_stages)
        ]
        inlet_stream_condition = [
            CompressorStreamCondition.create_empty(len(result_list)) for i in range(number_of_stages)
        ]
        outlet_stream_condition = [
            CompressorStreamCondition.create_empty(len(result_list)) for i in range(number_of_stages)
        ]

        for i in range(number_of_stages):
            compressor_stage_result[i].energy_usage = [
                result_list[t].stage_results[i].power_megawatt
                for t in range(len(result_list))
                if result_list[t].stage_results[i].power_megawatt is not None
            ]
            compressor_stage_result[i].energy_usage_unit = Unit.MEGA_WATT
            compressor_stage_result[i].power = [
                result_list[t].stage_results[i].power_megawatt
                for t in range(len(result_list))
                if result_list[t].stage_results[i].power_megawatt is not None
            ]
            compressor_stage_result[i].mass_rate_kg_per_hr = [
                result_list[t].stage_results[i].mass_rate_asv_corrected_kg_per_hour
                for t in range(len(result_list))
                if result_list[t].stage_results[i].mass_rate_asv_corrected_kg_per_hour is not None
            ]
            compressor_stage_result[i].mass_rate_before_asv_kg_per_hr = [
                result_list[t].stage_results[i].mass_rate_kg_per_hour
                for t in range(len(result_list))
                if result_list[t].stage_results[i].mass_rate_kg_per_hour is not None
            ]

            # For inlet- and outlet stream condition it is necessary to check if inlet- or outlet
            # streams exist. They may not exist, e.g. in case of zero rate etc. In this case, nan should
            # be set, to ensure match between timesteps and values.
            inlet_stream_condition[i].pressure = [
                result_list[t].stage_results[i].inlet_stream.pressure_bara
                if result_list[t].stage_results[i].inlet_stream is not None
                and result_list[t].stage_results[i].inlet_stream.pressure_bara is not None
                else np.nan
                for t in range(len(result_list))
            ]
            inlet_stream_condition[i].pressure_before_choking = [
                result_list[t].stage_results[i].inlet_pressure_before_choking
                for t in range(len(result_list))
                if result_list[t].stage_results[i].inlet_pressure_before_choking is not None
            ]
            # Note: Here we reverse the lingo from "before ASV" to "ASV corrected"
            inlet_stream_condition[i].actual_rate_m3_per_hr = [
                result_list[t].stage_results[i].inlet_actual_rate_asv_corrected_m3_per_hour
                for t in range(len(result_list))
                if result_list[t].stage_results[i].inlet_actual_rate_asv_corrected_m3_per_hour is not None
            ]
            inlet_stream_condition[i].actual_rate_before_asv_m3_per_hr = [
                result_list[t].stage_results[i].inlet_actual_rate_m3_per_hour
                for t in range(len(result_list))
                if result_list[t].stage_results[i].inlet_actual_rate_m3_per_hour is not None
            ]
            inlet_stream_condition[i].density_kg_per_m3 = [
                result_list[t].stage_results[i].inlet_stream.density_kg_per_m3
                if result_list[t].stage_results[i].inlet_stream is not None
                and result_list[t].stage_results[i].inlet_stream.density_kg_per_m3 is not None
                else np.nan
                for t in range(len(result_list))
            ]
            inlet_stream_condition[i].kappa = [
                result_list[t].stage_results[i].inlet_stream.kappa
                if result_list[t].stage_results[i].inlet_stream is not None
                and result_list[t].stage_results[i].inlet_stream.kappa is not None
                else np.nan
                for t in range(len(result_list))
            ]
            inlet_stream_condition[i].z = [
                result_list[t].stage_results[i].inlet_stream.z
                if result_list[t].stage_results[i].inlet_stream is not None
                and result_list[t].stage_results[i].inlet_stream.z is not None
                else np.nan
                for t in range(len(result_list))
            ]
            inlet_stream_condition[i].temperature_kelvin = [
                result_list[t].stage_results[i].inlet_stream.temperature_kelvin
                if result_list[t].stage_results[i].inlet_stream is not None
                and result_list[t].stage_results[i].inlet_stream.temperature_kelvin is not None
                else np.nan
                for t in range(len(result_list))
            ]

            outlet_stream_condition[i].pressure = [
                result_list[t].stage_results[i].outlet_stream.pressure_bara
                if result_list[t].stage_results[i].outlet_stream is not None
                and result_list[t].stage_results[i].outlet_stream.pressure_bara is not None
                else np.nan
                for t in range(len(result_list))
            ]
            outlet_stream_condition[i].pressure_before_choking = [
                result_list[t].stage_results[i].outlet_pressure_before_choking
                for t in range(len(result_list))
                if result_list[t].stage_results[i].outlet_pressure_before_choking is not None
            ]
            outlet_stream_condition[i].actual_rate_m3_per_hr = [
                result_list[t].stage_results[i].outlet_actual_rate_m3_per_hour
                for t in range(len(result_list))
                if result_list[t].stage_results[i].outlet_actual_rate_m3_per_hour is not None
            ]
            outlet_stream_condition[i].actual_rate_before_asv_m3_per_hr = [np.nan] * len(result_list)
            outlet_stream_condition[i].density_kg_per_m3 = [
                result_list[t].stage_results[i].outlet_stream.density_kg_per_m3
                if result_list[t].stage_results[i].outlet_stream is not None
                and result_list[t].stage_results[i].outlet_stream.density_kg_per_m3 is not None
                else np.nan
                for t in range(len(result_list))
            ]
            outlet_stream_condition[i].kappa = [
                result_list[t].stage_results[i].outlet_stream.kappa
                if result_list[t].stage_results[i].outlet_stream is not None
                and result_list[t].stage_results[i].outlet_stream.kappa is not None
                else np.nan
                for t in range(len(result_list))
            ]
            outlet_stream_condition[i].z = [
                result_list[t].stage_results[i].outlet_stream.z
                if result_list[t].stage_results[i].outlet_stream is not None
                and result_list[t].stage_results[i].outlet_stream.z is not None
                else np.nan
                for t in range(len(result_list))
            ]
            outlet_stream_condition[i].temperature_kelvin = [
                result_list[t].stage_results[i].outlet_stream.temperature_kelvin
                if result_list[t].stage_results[i].outlet_stream is not None
                and result_list[t].stage_results[i].outlet_stream.temperature_kelvin is not None
                else np.nan
                for t in range(len(result_list))
            ]

            compressor_stage_result[i].inlet_stream_condition = inlet_stream_condition[i]
            compressor_stage_result[i].outlet_stream_condition = outlet_stream_condition[i]

            compressor_stage_result[i].polytropic_enthalpy_change_kJ_per_kg = [
                result_list[t].stage_results[i].polytropic_enthalpy_change_kJ_per_kg
                for t in range(len(result_list))
                if result_list[t].stage_results[i].polytropic_enthalpy_change_kJ_per_kg is not None
            ]
            compressor_stage_result[i].polytropic_head_kJ_per_kg = [
                result_list[t].stage_results[i].polytropic_head_kJ_per_kg
                for t in range(len(result_list))
                if result_list[t].stage_results[i].polytropic_head_kJ_per_kg is not None
            ]
            compressor_stage_result[i].polytropic_efficiency = [
                result_list[t].stage_results[i].polytropic_efficiency
                for t in range(len(result_list))
                if result_list[t].stage_results[i].polytropic_efficiency is not None
            ]
            compressor_stage_result[i].polytropic_enthalpy_change_before_choke_kJ_per_kg = [
                result_list[t].stage_results[i].polytropic_enthalpy_change_before_choke_kJ_per_kg
                for t in range(len(result_list))
                if result_list[t].stage_results[i].polytropic_enthalpy_change_before_choke_kJ_per_kg is not None
            ]
            compressor_stage_result[i].speed = [result.speed for result in result_list if result.speed is not None]
            compressor_stage_result[i].asv_recirculation_loss_mw = [
                result_list[t].stage_results[i].asv_recirculation_loss_mw
                for t in range(len(result_list))
                if result_list[t].stage_results[i].asv_recirculation_loss_mw is not None
            ]
            # Validity flags
            compressor_stage_result[i].is_valid = [
                result_list[t].stage_results[i].is_valid
                for t in range(len(result_list))
                if result_list[t].stage_results[i].is_valid is not None
            ]
            compressor_stage_result[i].chart_area_flags = [
                result_list[t].stage_results[i].chart_area_flag
                for t in range(len(result_list))
                if result_list[t].stage_results[i].chart_area_flag is not None
            ]
            compressor_stage_result[i].rate_has_recirculation = [
                bool(result_list[t].stage_results[i].rate_has_recirculation)
                for t in range(len(result_list))
                if bool(result_list[t].stage_results[i].rate_has_recirculation) is not None
            ]
            compressor_stage_result[i].rate_exceeds_maximum = [
                bool(result_list[t].stage_results[i].rate_exceeds_maximum)
                for t in range(len(result_list))
                if bool(result_list[t].stage_results[i].rate_exceeds_maximum) is not None
            ]
            compressor_stage_result[i].pressure_is_choked = [
                bool(result_list[t].stage_results[i].pressure_is_choked)
                for t in range(len(result_list))
                if bool(result_list[t].stage_results[i].pressure_is_choked) is not None
            ]
            compressor_stage_result[i].head_exceeds_maximum = [
                bool(result_list[t].stage_results[i].head_exceeds_maximum)
                for t in range(len(result_list))
                if bool(result_list[t].stage_results[i].head_exceeds_maximum) is not None
            ]
            compressor_stage_result[i].fluid_composition = {}
            compressor_stage_result[i].chart = compressor_charts[i] if compressor_charts is not None else None
        return compressor_stage_result

    model_config = ConfigDict(extra="forbid")

    @field_validator("failure_status")
    @classmethod
    def set_failure_status(cls, v, info: ValidationInfo):
        stage_results = info.data.get("stage_results")
        if not all(r.is_valid for r in stage_results):
            for stage in stage_results:
                if not stage.is_valid:
                    if stage.chart_area_flag in (
                        ChartAreaFlag.ABOVE_MAXIMUM_FLOW_RATE,
                        ChartAreaFlag.BELOW_MINIMUM_SPEED_AND_ABOVE_MAXIMUM_FLOW_RATE,
                    ):
                        return CompressorTrainCommonShaftFailureStatus.ABOVE_MAXIMUM_FLOW_RATE
                    elif stage.chart_area_flag in (
                        ChartAreaFlag.BELOW_MINIMUM_FLOW_RATE,
                        ChartAreaFlag.BELOW_MINIMUM_SPEED_AND_BELOW_MINIMUM_FLOW_RATE,
                    ):
                        return CompressorTrainCommonShaftFailureStatus.BELOW_MINIMUM_FLOW_RATE
        return v

    @property
    def chart_area_status(self) -> ChartAreaFlag:
        """Checks where the operational points are placed in relation to the compressor charts in a compressor train.

        Returns:
            A chart area flag describing the placement of the operational points in the compressor train.
            If several of the compressors in the compressor train is out of capacity, only the first failure will
            be returned.
        """
        chart_area_failure = [stage.chart_area_flag for stage in self.stage_results if not stage.point_is_valid]
        if len(chart_area_failure) > 0:
            return chart_area_failure[0]
        else:
            chart_area_flag = [stage.chart_area_flag for stage in self.stage_results if stage.point_is_valid]
            if ChartAreaFlag.NO_FLOW_RATE in chart_area_flag:
                return ChartAreaFlag.NO_FLOW_RATE
            else:
                return chart_area_flag[0]

    @property
    def is_valid(self) -> bool:
        if self.failure_status:
            return False
        elif len(self.stage_results) > 0:
            return bool(np.all([r.is_valid for r in self.stage_results]))
        else:
            return True

    @property
    def power_megawatt(self) -> float:
        return sum([np.asarray(stage_result.power_megawatt, dtype=float) for stage_result in self.stage_results])  # type: ignore[misc]

    @property
    def discharge_pressure(self) -> float:
        if self.stage_results[-1].outlet_stream is not None:
            return self.stage_results[-1].outlet_stream.pressure_bara
        else:
            return np.nan

    @property
    def discharge_pressure_before_choking(self) -> float:
        return self.stage_results[-1].outlet_pressure_before_choking

    @property
    def suction_pressure(self) -> float:
        if self.stage_results[0].inlet_stream is not None:
            return self.stage_results[0].inlet_stream.pressure_bara
        else:
            return np.nan

    @property
    def suction_pressure_before_choking(self) -> float:
        return self.stage_results[0].inlet_pressure_before_choking

    @property
    def mass_rate_kg_per_hour(self) -> float:
        return self.stage_results[0].mass_rate_kg_per_hour

    @property
    def mass_rate_asv_corrected_kg_per_hour(self) -> float:
        return self.stage_results[0].mass_rate_asv_corrected_kg_per_hour

    @property
    def inlet_actual_rate_asv_corrected_m3_per_hour(self) -> float:
        return self.stage_results[0].inlet_actual_rate_asv_corrected_m3_per_hour

    @property
    def inlet_actual_rate(self) -> float:
        return self.stage_results[0].inlet_actual_rate_m3_per_hour

    @property
    def inlet_density(self) -> float:
        if self.stage_results[0].inlet_stream is not None:
            return self.stage_results[0].inlet_stream.density_kg_per_m3
        else:
            return np.nan

    @property
    def inlet_z(self) -> float:
        if self.stage_results[0].inlet_stream is not None:
            return self.stage_results[0].inlet_stream.z
        else:
            return np.nan

    @property
    def inlet_kappa(self) -> float:
        if self.stage_results[0].inlet_stream is not None:
            return self.stage_results[0].inlet_stream.kappa
        else:
            return np.nan

    @property
    def inlet_temperature_kelvin(self) -> float:
        if self.stage_results[0].inlet_stream is not None:
            return self.stage_results[0].inlet_stream.temperature_kelvin
        else:
            return np.nan

    @property
    def inlet_fluid_composition(self) -> dto.FluidComposition:
        if self.stage_results[0].inlet_stream is not None:
            return self.stage_results[0].inlet_stream.composition
        else:
            return dto.FluidComposition()

    @property
    def outlet_actual_rate(self) -> float:
        return self.stage_results[-1].outlet_actual_rate_m3_per_hour

    @property
    def outlet_density(self) -> float:
        if self.stage_results[-1].outlet_stream is not None:
            return self.stage_results[-1].outlet_stream.density_kg_per_m3
        else:
            return np.nan

    @property
    def outlet_kappa(self) -> float:
        if self.stage_results[-1].outlet_stream is not None:
            return self.stage_results[-1].outlet_stream.kappa
        else:
            return np.nan

    @property
    def outlet_z(self) -> float:
        if self.stage_results[-1].outlet_stream is not None:
            return self.stage_results[-1].outlet_stream.z
        else:
            return np.nan

    @property
    def outlet_temperature_kelvin(self) -> float:
        if self.stage_results[-1].outlet_stream is not None:
            return self.stage_results[-1].outlet_stream.temperature_kelvin
        else:
            return np.nan

    @property
    def outlet_fluid_composition(self) -> dto.FluidComposition:
        if self.stage_results[-1].outlet_stream is not None:
            return self.stage_results[-1].outlet_stream.composition
        else:
            return dto.FluidComposition()

    @property
    def polytropic_head_kilo_joule_per_kg(self) -> List[float]:
        return [stage.polytropic_head_kJ_per_kg for stage in self.stage_results]

    @property
    def polytropic_enthalpy_change_kilo_joule_per_kg(self) -> float:
        return sum([stage.polytropic_enthalpy_change_kJ_per_kg for stage in self.stage_results])

    @property
    def polytropic_enthalpy_change_before_choke_kilo_joule_per_kg(self) -> float:
        if self.stage_results[0].polytropic_enthalpy_change_before_choke_kJ_per_kg is not None:
            return sum([stage.polytropic_enthalpy_change_before_choke_kJ_per_kg for stage in self.stage_results])
        else:
            return np.nan

    @property
    def polytropic_efficiency(self) -> List[float]:
        return [stage.polytropic_efficiency for stage in self.stage_results]

    @property
    def asv_recirculation_loss_mw(self) -> float:
        return sum([stage.asv_recirculation_loss_mw for stage in self.stage_results])

    @property
    def rate_has_recirculation(self) -> bool:
        return self.asv_recirculation_loss_mw > 0 or any(stage.rate_has_recirculation for stage in self.stage_results)

    @property
    def rate_exceeds_maximum(self) -> bool:
        if len(self.stage_results) > 0:
            return any(stage.rate_exceeds_maximum for stage in self.stage_results) or self.chart_area_status in (
                ChartAreaFlag.ABOVE_MAXIMUM_FLOW_RATE,
                ChartAreaFlag.BELOW_MINIMUM_SPEED_AND_ABOVE_MAXIMUM_FLOW_RATE,
            )
        else:
            return False

    @property
    def pressure_is_choked(self) -> bool:
        # Small margin when checking for choke in order to avoid false positives.
        return self.discharge_pressure < (self.discharge_pressure_before_choking - 1e-5) or any(
            stage.pressure_is_choked for stage in self.stage_results
        )

    @property
    def head_exceeds_maximum(self) -> bool:
        return any(stage.head_exceeds_maximum for stage in self.stage_results)

    @property
    def mass_rate_asv_corrected_is_constant_for_stages(self) -> bool:
        # A common ASV over all stages require a constant mass rate through the train
        return len({round(stage.mass_rate_asv_corrected_kg_per_hour, 4) for stage in self.stage_results}) <= 1

    @classmethod
    def create_empty(cls, number_of_stages: int) -> CompressorTrainResultSingleTimeStep:
        return cls(
            speed=np.nan,
            stage_results=[CompressorTrainStageResultSingleTimeStep.create_empty()] * number_of_stages,
        )
