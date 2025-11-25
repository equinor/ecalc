from __future__ import annotations

import numpy as np

from libecalc.common.units import Unit
from libecalc.domain.process.core.results.compressor import (
    CompressorStageResult,
    CompressorStreamCondition,
    CompressorTrainCommonShaftFailureStatus,
    TargetPressureStatus,
)
from libecalc.domain.process.value_objects.chart import Chart
from libecalc.domain.process.value_objects.chart.chart_area_flag import ChartAreaFlag
from libecalc.domain.process.value_objects.fluid_stream import FluidStream
from libecalc.domain.process.value_objects.fluid_stream.fluid_model import FluidComposition


class CompressorTrainStageResultSingleTimeStep:
    """One stage, one time step.

    Actual rate per hour [Am3/h]
    standard rate per day [sm3/day]
    mass rate [kg/hour]
    head [J/kg]
    Polytropic efficiency (0, 1]
    power [MW]
    """

    def __init__(
        self,
        inlet_stream: FluidStream | None,
        outlet_stream: FluidStream | None,
        inlet_stream_including_asv: FluidStream | None,
        outlet_stream_including_asv: FluidStream | None,
        polytropic_head_kJ_per_kg: float,
        polytropic_efficiency: float,
        polytropic_enthalpy_change_kJ_per_kg: float,
        polytropic_enthalpy_change_before_choke_kJ_per_kg: float,
        power_megawatt: float,
        chart_area_flag: ChartAreaFlag,
        point_is_valid: bool,
        rate_has_recirculation: bool | None = None,
        rate_exceeds_maximum: bool | None = None,
        pressure_is_choked: bool | None = None,
        head_exceeds_maximum: bool | None = None,
    ):
        self.inlet_stream = inlet_stream
        self.outlet_stream = outlet_stream
        self.inlet_stream_including_asv = inlet_stream_including_asv
        self.outlet_stream_including_asv = outlet_stream_including_asv
        self.polytropic_head_kJ_per_kg = polytropic_head_kJ_per_kg
        self.polytropic_efficiency = polytropic_efficiency
        self.polytropic_enthalpy_change_kJ_per_kg = polytropic_enthalpy_change_kJ_per_kg
        self.polytropic_enthalpy_change_before_choke_kJ_per_kg = polytropic_enthalpy_change_before_choke_kJ_per_kg
        self.power_megawatt = power_megawatt
        self.chart_area_flag = chart_area_flag
        self.rate_has_recirculation = rate_has_recirculation
        self.rate_exceeds_maximum = rate_exceeds_maximum
        self.pressure_is_choked = pressure_is_choked
        self.head_exceeds_maximum = head_exceeds_maximum
        self.point_is_valid = bool(point_is_valid)

    @classmethod
    def create_empty(cls) -> CompressorTrainStageResultSingleTimeStep:
        return cls(
            inlet_stream=None,
            outlet_stream=None,
            inlet_stream_including_asv=None,
            outlet_stream_including_asv=None,
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
            point_is_valid=True,
        )

    @property
    def inlet_actual_rate_m3_per_hour(self) -> float:
        """Actual inlet rate in Am3/hour."""
        if self.inlet_stream is None:
            return np.nan
        else:
            return self.inlet_stream.volumetric_rate

    @property
    def inlet_actual_rate_asv_corrected_m3_per_hour(self) -> float:
        """Actual inlet rate in Am3/hour, corrected for ASV."""
        if self.inlet_stream_including_asv is None:
            return np.nan
        else:
            return self.inlet_stream_including_asv.volumetric_rate

    @property
    def standard_rate_sm3_per_day(self) -> float:
        """Standard inlet rate in Sm3/day."""
        if self.inlet_stream is None:
            return np.nan
        else:
            return self.inlet_stream.standard_rate

    @property
    def standard_rate_asv_corrected_sm3_per_day(self) -> float:
        """Standard inlet rate in Sm3/day, corrected for ASV."""
        if self.inlet_stream_including_asv is None:
            return np.nan
        else:
            return self.inlet_stream_including_asv.standard_rate

    @property
    def outlet_actual_rate_m3_per_hour(self) -> float:
        """Actual outlet rate in Am3/hour."""
        if self.outlet_stream is None:
            return np.nan
        else:
            return self.outlet_stream.volumetric_rate

    @property
    def outlet_actual_rate_asv_corrected_m3_per_hour(self) -> float:
        """Actual outlet rate in Am3/hour, corrected for ASV."""
        if self.outlet_stream_including_asv is None:
            return np.nan
        else:
            return self.outlet_stream_including_asv.volumetric_rate

    @property
    def mass_rate_kg_per_hour(self) -> float:
        """Mass rate in kg/hour"""
        if self.inlet_stream is None:
            return np.nan
        else:
            return self.inlet_stream.mass_rate_kg_per_h

    @property
    def mass_rate_asv_corrected_kg_per_hour(self) -> float:
        """Mass rate in kg/hour, corrected for ASV."""
        if self.inlet_stream_including_asv is None:
            return np.nan
        else:
            return self.inlet_stream_including_asv.mass_rate_kg_per_h

    @property
    def is_valid(self) -> bool:
        return self.within_capacity

    @property
    def within_capacity(self) -> bool:
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


class CompressorTrainResultSingleTimeStep:
    """All stages, one time step.

    speed [rpm]
    pressure [bar]
    rate [Sm3/day]
    mass rate [kg/hour]
    """

    def __init__(
        self,
        inlet_stream: FluidStream | None,
        outlet_stream: FluidStream | None,
        speed: float,
        stage_results: list[CompressorTrainStageResultSingleTimeStep],
        target_pressure_status: TargetPressureStatus,
        above_maximum_power: bool = False,
    ):
        self.inlet_stream = inlet_stream
        self.outlet_stream = outlet_stream
        self.speed = speed
        self.stage_results = stage_results
        self.above_maximum_power = above_maximum_power
        self.target_pressure_status = target_pressure_status

    @staticmethod
    def from_result_list_to_dto(
        result_list: list[CompressorTrainResultSingleTimeStep],
        compressor_charts: list[Chart] | None,
    ) -> tuple[CompressorStreamCondition, CompressorStreamCondition, list[CompressorStageResult]]:
        number_of_stages = max([len(t.stage_results) for t in result_list])

        def get_or_fill(property_name: str, obj: object | None, fill: float = np.nan) -> float:
            if obj is None:
                return fill
            else:
                return getattr(obj, property_name)

        compressor_stage_results: list[CompressorStageResult] = []
        for i in range(number_of_stages):
            list_stage_result = CompressorStageResult.create_empty(len(result_list))
            list_stage_result.energy_usage_unit = Unit.MEGA_WATT
            list_inlet_stream = CompressorStreamCondition.create_empty(len(result_list))
            list_outlet_stream = CompressorStreamCondition.create_empty(len(result_list))

            for t in range(len(result_list)):
                single_train_result = result_list[t]
                single_stage_result = single_train_result.stage_results[i]

                list_stage_result.energy_usage[t] = single_stage_result.power_megawatt
                list_stage_result.power[t] = single_stage_result.power_megawatt

                list_stage_result.mass_rate_kg_per_hr[t] = single_stage_result.mass_rate_asv_corrected_kg_per_hour
                list_stage_result.mass_rate_before_asv_kg_per_hr[t] = single_stage_result.mass_rate_kg_per_hour

                # For inlet- and outlet stream condition it is necessary to check if inlet- or outlet
                # streams exist. They may not exist, e.g. in case of zero rate etc. In this case, nan should
                # be set, to ensure match between periods and values.
                list_inlet_stream.pressure[t] = get_or_fill("pressure_bara", single_stage_result.inlet_stream)
                # Note: Here we reverse the lingo from "before ASV" to "ASV corrected"
                list_inlet_stream.actual_rate_m3_per_hr[t] = (
                    single_stage_result.inlet_actual_rate_asv_corrected_m3_per_hour
                )
                list_inlet_stream.actual_rate_before_asv_m3_per_hr[t] = (
                    single_stage_result.inlet_actual_rate_m3_per_hour
                )
                list_inlet_stream.standard_rate_sm3_per_day[t] = (
                    single_stage_result.standard_rate_asv_corrected_sm3_per_day
                )
                list_inlet_stream.standard_rate_before_asv_sm3_per_day[t] = (
                    single_stage_result.standard_rate_sm3_per_day
                )
                list_inlet_stream.density_kg_per_m3[t] = get_or_fill("density", single_stage_result.inlet_stream)
                list_inlet_stream.kappa[t] = get_or_fill("kappa", single_stage_result.inlet_stream)
                list_inlet_stream.z[t] = get_or_fill("z", single_stage_result.inlet_stream)
                list_inlet_stream.temperature_kelvin[t] = get_or_fill(
                    "temperature_kelvin", single_stage_result.inlet_stream
                )
                list_outlet_stream.pressure[t] = get_or_fill("pressure_bara", single_stage_result.outlet_stream)
                list_outlet_stream.actual_rate_m3_per_hr[t] = (
                    single_stage_result.outlet_actual_rate_asv_corrected_m3_per_hour
                )
                list_outlet_stream.actual_rate_before_asv_m3_per_hr[t] = (
                    single_stage_result.outlet_actual_rate_m3_per_hour
                )
                list_outlet_stream.standard_rate_sm3_per_day[t] = (
                    single_stage_result.standard_rate_asv_corrected_sm3_per_day
                )

                list_outlet_stream.standard_rate_before_asv_sm3_per_day[t] = (
                    single_stage_result.standard_rate_sm3_per_day
                )
                list_outlet_stream.density_kg_per_m3[t] = get_or_fill("density", single_stage_result.outlet_stream)
                list_outlet_stream.kappa[t] = get_or_fill("kappa", single_stage_result.outlet_stream)
                list_outlet_stream.z[t] = get_or_fill("z", single_stage_result.outlet_stream)
                list_outlet_stream.temperature_kelvin[t] = get_or_fill(
                    "temperature_kelvin", single_stage_result.outlet_stream
                )

                # stage again
                list_stage_result.polytropic_enthalpy_change_kJ_per_kg[t] = (
                    single_stage_result.polytropic_enthalpy_change_kJ_per_kg
                )
                list_stage_result.polytropic_head_kJ_per_kg[t] = single_stage_result.polytropic_head_kJ_per_kg
                list_stage_result.polytropic_efficiency[t] = single_stage_result.polytropic_efficiency
                list_stage_result.polytropic_enthalpy_change_before_choke_kJ_per_kg[t] = (
                    single_stage_result.polytropic_enthalpy_change_before_choke_kJ_per_kg
                )
                list_stage_result.speed[t] = single_train_result.speed
                list_stage_result.asv_recirculation_loss_mw[t] = single_stage_result.asv_recirculation_loss_mw
                list_stage_result.is_valid[t] = single_stage_result.is_valid
                list_stage_result.chart_area_flags[t] = single_stage_result.chart_area_flag
                list_stage_result.rate_has_recirculation[t] = bool(
                    single_stage_result.rate_has_recirculation
                )  # Might be None, convert to bool
                list_stage_result.rate_exceeds_maximum[t] = bool(
                    single_stage_result.rate_exceeds_maximum
                )  # Might be None, convert to bool
                list_stage_result.pressure_is_choked[t] = bool(
                    single_stage_result.pressure_is_choked
                )  # Might be None, convert to bool
                list_stage_result.head_exceeds_maximum[t] = bool(
                    single_stage_result.head_exceeds_maximum
                )  # Might be None, convert to bool

            list_stage_result.inlet_stream_condition = list_inlet_stream
            list_stage_result.outlet_stream_condition = list_outlet_stream

            list_stage_result.fluid_composition = {}
            list_stage_result.chart = compressor_charts[i].chart_data if compressor_charts is not None else None

            compressor_stage_results.append(list_stage_result)

        inlet_stream_condition_for_train = CompressorStreamCondition.create_empty(len(result_list))
        outlet_stream_condition_for_train = CompressorStreamCondition.create_empty(len(result_list))
        for t in range(len(result_list)):
            single_train_result = result_list[t]
            single_inlet_stream = single_train_result.inlet_stream
            single_outlet_stream = single_train_result.outlet_stream
            inlet_stream_condition_for_train.pressure[t] = get_or_fill("pressure_bara", single_inlet_stream)

            # Note: Here we reverse the lingo from "before ASV" to "ASV corrected"

            inlet_stream_condition_for_train.actual_rate_m3_per_hr[t] = single_train_result.inlet_actual_rate
            inlet_stream_condition_for_train.density_kg_per_m3[t] = get_or_fill("density", single_inlet_stream)
            inlet_stream_condition_for_train.kappa[t] = get_or_fill("kappa", single_inlet_stream)
            inlet_stream_condition_for_train.z[t] = get_or_fill("z", single_inlet_stream)
            inlet_stream_condition_for_train.temperature_kelvin[t] = get_or_fill(
                "temperature_kelvin", single_inlet_stream
            )

            # not relevant for train
            inlet_stream_condition_for_train.actual_rate_before_asv_m3_per_hr[t] = np.nan
            inlet_stream_condition_for_train.standard_rate_before_asv_sm3_per_day[t] = np.nan

            outlet_stream_condition_for_train.pressure[t] = get_or_fill("pressure_bara", single_outlet_stream)
            outlet_stream_condition_for_train.actual_rate_m3_per_hr[t] = single_train_result.outlet_actual_rate

            outlet_stream_condition_for_train.density_kg_per_m3[t] = get_or_fill("density", single_outlet_stream)
            outlet_stream_condition_for_train.kappa[t] = get_or_fill("kappa", single_outlet_stream)
            outlet_stream_condition_for_train.z[t] = get_or_fill("z", single_outlet_stream)
            outlet_stream_condition_for_train.temperature_kelvin[t] = get_or_fill(
                "temperature_kelvin", single_outlet_stream
            )
            # not relevant for train
            outlet_stream_condition_for_train.actual_rate_before_asv_m3_per_hr[t] = np.nan
            outlet_stream_condition_for_train.standard_rate_before_asv_sm3_per_day[t] = np.nan

            inlet_rates = compressor_stage_results[0].inlet_stream_condition.standard_rate_before_asv_sm3_per_day
            inlet_stream_condition_for_train.standard_rate_sm3_per_day[t] = inlet_rates[t]
            outlet_rates = compressor_stage_results[-1].outlet_stream_condition.standard_rate_before_asv_sm3_per_day
            outlet_stream_condition_for_train.standard_rate_sm3_per_day[t] = outlet_rates[t]

        return inlet_stream_condition_for_train, outlet_stream_condition_for_train, compressor_stage_results

    @property
    def failure_status(self):
        if not all(r.is_valid for r in self.stage_results):
            for stage in self.stage_results:
                if not stage.within_capacity:
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
        if self.target_pressure_status == TargetPressureStatus.ABOVE_TARGET_SUCTION_PRESSURE:
            return CompressorTrainCommonShaftFailureStatus.TARGET_DISCHARGE_PRESSURE_TOO_HIGH
        elif self.target_pressure_status == TargetPressureStatus.BELOW_TARGET_SUCTION_PRESSURE:
            return CompressorTrainCommonShaftFailureStatus.TARGET_SUCTION_PRESSURE_TOO_HIGH
        elif self.target_pressure_status == TargetPressureStatus.ABOVE_TARGET_DISCHARGE_PRESSURE:
            return CompressorTrainCommonShaftFailureStatus.TARGET_DISCHARGE_PRESSURE_TOO_LOW
        elif self.target_pressure_status == TargetPressureStatus.BELOW_TARGET_DISCHARGE_PRESSURE:
            return CompressorTrainCommonShaftFailureStatus.TARGET_DISCHARGE_PRESSURE_TOO_HIGH
        elif self.target_pressure_status == TargetPressureStatus.ABOVE_TARGET_INTERMEDIATE_PRESSURE:
            return CompressorTrainCommonShaftFailureStatus.TARGET_INTERMEDIATE_PRESSURE_TOO_LOW
        elif self.target_pressure_status == TargetPressureStatus.BELOW_TARGET_INTERMEDIATE_PRESSURE:
            return CompressorTrainCommonShaftFailureStatus.TARGET_INTERMEDIATE_PRESSURE_TOO_HIGH
        elif self.above_maximum_power:
            return CompressorTrainCommonShaftFailureStatus.ABOVE_MAXIMUM_POWER

        return CompressorTrainCommonShaftFailureStatus.NO_FAILURE

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
        if not self.failure_status == CompressorTrainCommonShaftFailureStatus.NO_FAILURE:
            return False
        elif len(self.stage_results) > 0:
            return bool(np.all([r.is_valid for r in self.stage_results]))
        else:
            return True

    @property
    def within_capacity(self) -> bool:
        return bool(np.all([r.within_capacity for r in self.stage_results]))

    @property
    def power_megawatt(self) -> float:
        return sum([stage_result.power_megawatt for stage_result in self.stage_results])

    @property
    def discharge_pressure(self) -> float:
        if self.outlet_stream is not None:
            return self.outlet_stream.pressure_bara
        else:
            return np.nan

    @property
    def suction_pressure(self) -> float:
        if self.inlet_stream is not None:
            return self.inlet_stream.pressure_bara
        else:
            return np.nan

    @property
    def mass_rate_kg_per_hour(self) -> float:
        return self.stage_results[0].mass_rate_kg_per_hour

    @property
    def inlet_actual_rate(self) -> float:
        return self.stage_results[0].inlet_actual_rate_m3_per_hour

    @property
    def inlet_density(self) -> float:
        if self.inlet_stream is not None:
            return self.inlet_stream.density
        else:
            return np.nan

    @property
    def inlet_z(self) -> float:
        if self.inlet_stream is not None:
            return self.inlet_stream.z
        else:
            return np.nan

    @property
    def inlet_kappa(self) -> float:
        if self.inlet_stream is not None:
            return self.inlet_stream.kappa
        else:
            return np.nan

    @property
    def inlet_temperature_kelvin(self) -> float:
        if self.inlet_stream is not None:
            return self.inlet_stream.temperature_kelvin
        else:
            return np.nan

    @property
    def inlet_fluid_composition(self) -> FluidComposition:
        if self.inlet_stream is not None:
            return self.inlet_stream.thermo_system.composition
        else:
            return FluidComposition()

    @property
    def outlet_actual_rate(self) -> float:
        return self.stage_results[-1].outlet_actual_rate_m3_per_hour

    @property
    def outlet_density(self) -> float:
        if self.outlet_stream is not None:
            return self.outlet_stream.density
        else:
            return np.nan

    @property
    def outlet_kappa(self) -> float:
        if self.outlet_stream is not None:
            return self.outlet_stream.kappa
        else:
            return np.nan

    @property
    def outlet_z(self) -> float:
        if self.outlet_stream is not None:
            return self.outlet_stream.z
        else:
            return np.nan

    @property
    def outlet_temperature_kelvin(self) -> float:
        if self.outlet_stream is not None:
            return self.outlet_stream.temperature_kelvin
        else:
            return np.nan

    @property
    def outlet_fluid_composition(self) -> FluidComposition:
        if self.outlet_stream is not None:
            return self.outlet_stream.thermo_system.composition
        else:
            return FluidComposition()

    @property
    def polytropic_head_kilo_joule_per_kg(self) -> list[float]:
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
    def polytropic_efficiency(self) -> list[float]:
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
        return self.discharge_pressure < self.stage_results[0].discharge_pressure or any(
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
            inlet_stream=None,
            outlet_stream=None,
            speed=np.nan,
            stage_results=[CompressorTrainStageResultSingleTimeStep.create_empty()] * number_of_stages,
            target_pressure_status=TargetPressureStatus.NOT_CALCULATED,
        )
