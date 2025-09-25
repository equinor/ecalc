import numpy as np

from libecalc.common.errors.exceptions import IllegalStateException
from libecalc.common.logger import logger
from libecalc.common.units import UnitConstants
from libecalc.domain.component_validation_error import (
    ProcessCompressorEfficiencyValidationException,
    ProcessMissingVariableValidationException,
)
from libecalc.domain.process.compressor.core.results import CompressorTrainStageResultSingleTimeStep
from libecalc.domain.process.compressor.core.train.utils.common import (
    EPSILON,
    calculate_asv_corrected_rate,
    calculate_outlet_pressure_and_stream,
    calculate_power_in_megawatt,
)
from libecalc.domain.process.compressor.core.train.utils.enthalpy_calculations import (
    calculate_enthalpy_change_head_iteration,
)
from libecalc.domain.process.compressor.core.train.utils.numeric_methods import find_root
from libecalc.domain.process.compressor.dto import InterstagePressureControl
from libecalc.domain.process.value_objects.chart.chart_area_flag import ChartAreaFlag
from libecalc.domain.process.value_objects.chart.compressor import (
    CompressorChart,
)
from libecalc.domain.process.value_objects.fluid_stream import FluidStream, ProcessConditions


class CompressorTrainStage:
    """inlet_temperature_kelvin [K].

    Note: Used in both Single and Variable Speed compressor process modelling.
    """

    def __init__(
        self,
        compressor_chart: CompressorChart,
        inlet_temperature_kelvin: float,
        remove_liquid_after_cooling: bool,
        pressure_drop_ahead_of_stage: float | None = None,
        interstage_pressure_control: InterstagePressureControl | None = None,
    ):
        self.compressor_chart = compressor_chart
        self.inlet_temperature_kelvin = inlet_temperature_kelvin
        self.remove_liquid_after_cooling = remove_liquid_after_cooling
        self.pressure_drop_ahead_of_stage = pressure_drop_ahead_of_stage
        self.interstage_pressure_control = interstage_pressure_control

    @property
    def has_control_pressure(self):
        return self.interstage_pressure_control is not None

    def evaluate(
        self,
        inlet_stream_stage: FluidStream,
        speed: float,
        asv_rate_fraction: float | None = 0.0,
        asv_additional_mass_rate: float | None = 0.0,
        increase_rate_left_of_minimum_flow_assuming_asv: bool | None = True,
        increase_speed_below_assuming_choke: bool | None = False,
    ) -> CompressorTrainStageResultSingleTimeStep:
        """Evaluates a compressor train stage given the conditions and rate of the inlet stream, and the speed
        of the shaft driving the compressor if given.

        :param inlet_stream_stage: The conditions of the inlet fluid stream
        :param mass_rate_kg_per_hour: The mass rate (kg pr hour) entering the compressor stage
        :param speed: The speed of the shaft driving the compressor (a single speed compressor will only have on speed)
        :param asv_rate_fraction: Fraction of the available capacity of the compressor to fill using some kind of
            pressure control (on the interval [0,1]).
        :param asv_additional_mass_rate: Additional recirculated mass rate due to pressure control

        Note: asv_rate_fraction and asv_additional_mass_rate can not be defined different from zero at the same time

        Returns: Results of the evaluation
        """
        if speed < self.compressor_chart.minimum_speed or speed > self.compressor_chart.maximum_speed:
            msg = (
                f"Speed value ({speed}) outside allowed range ({self.compressor_chart.minimum_speed} -"
                f" {self.compressor_chart.maximum_speed}). You should not end up here, please contact support."
            )
            logger.exception(msg)
            raise IllegalStateException(msg)

        if asv_rate_fraction is not None and asv_additional_mass_rate is not None:
            if asv_rate_fraction > 0 and asv_additional_mass_rate > 0:
                msg = "asv_rate_fraction and asv_additional_mass_rate can not both be larger than 0"
                logger.exception(msg)
                raise IllegalStateException(msg)
            if asv_rate_fraction < 0.0 or asv_rate_fraction > 1.0:
                msg = "asv rate fraction must be a number in the interval [0.0, 1.0]"
                logger.exception(msg)
                raise IllegalStateException(msg)

        if self.pressure_drop_ahead_of_stage:
            inlet_pressure_stage = inlet_stream_stage.pressure_bara - self.pressure_drop_ahead_of_stage
        else:
            inlet_pressure_stage = inlet_stream_stage.pressure_bara

        inlet_stream_compressor = inlet_stream_stage.create_stream_with_new_conditions(
            conditions=ProcessConditions(
                pressure_bara=inlet_pressure_stage,
                temperature_kelvin=self.inlet_temperature_kelvin,
            ),
        )

        actual_rate_m3_per_hour_to_use = actual_rate_m3_per_hour = inlet_stream_compressor.volumetric_rate
        compressor_maximum_actual_rate_m3_per_hour = self.compressor_chart.maximum_rate_as_function_of_speed(speed)
        available_capacity_for_actual_rate_m3_per_hour = max(
            0, compressor_maximum_actual_rate_m3_per_hour - actual_rate_m3_per_hour
        )  #  if the actual_rate_m3_per_hour is above capacity, the available capacity should be zero, not negative

        additional_rate_m3_per_hour = 0.0
        # Add contribution from asv_rate_fraction (potentially used for pressure control)
        if asv_rate_fraction:
            additional_rate_m3_per_hour = asv_rate_fraction * available_capacity_for_actual_rate_m3_per_hour
        # Add contribution from asv_additional_mass_rate (potentially used for pressure control)
        if asv_additional_mass_rate:
            additional_rate_m3_per_hour = asv_additional_mass_rate / inlet_stream_compressor.density

        compressor_chart_head_and_efficiency_result = (
            self.compressor_chart.calculate_polytropic_head_and_efficiency_single_point(
                speed=speed,
                actual_rate_m3_per_hour=actual_rate_m3_per_hour,
                recirculated_rate_m3_per_hour=additional_rate_m3_per_hour,
                increase_rate_left_of_minimum_flow_assuming_asv=increase_rate_left_of_minimum_flow_assuming_asv,  # type: ignore[arg-type]
                increase_speed_below_assuming_choke=increase_speed_below_assuming_choke,  # type: ignore[arg-type]
            )
        )

        actual_rate_m3_per_hour_to_use += additional_rate_m3_per_hour

        polytropic_head_J_per_kg = compressor_chart_head_and_efficiency_result.polytropic_head
        polytropic_efficiency = compressor_chart_head_and_efficiency_result.polytropic_efficiency
        chart_area_flag = compressor_chart_head_and_efficiency_result.chart_area_flag

        if polytropic_efficiency == 0.0:
            msg = "Division by zero error. Efficiency from compressor chart is 0."

            raise ProcessCompressorEfficiencyValidationException(message=str(msg))

        # Enthalpy change
        enthalpy_change_J_per_kg = polytropic_head_J_per_kg / polytropic_efficiency
        (
            _,
            mass_rate_asv_corrected_kg_per_hour,
        ) = calculate_asv_corrected_rate(
            minimum_actual_rate_m3_per_hour=float(self.compressor_chart.minimum_rate_as_function_of_speed(speed)),
            actual_rate_m3_per_hour=actual_rate_m3_per_hour_to_use,
            density_kg_per_m3=inlet_stream_compressor.density,
        )
        inlet_stream_compressor_asv_corrected = FluidStream(
            thermo_system=inlet_stream_compressor.thermo_system,
            mass_rate_kg_per_h=mass_rate_asv_corrected_kg_per_hour,
        )
        power_megawatt = calculate_power_in_megawatt(
            enthalpy_change_joule_per_kg=enthalpy_change_J_per_kg,
            mass_rate_kg_per_hour=inlet_stream_compressor_asv_corrected.mass_rate_kg_per_h,
        )

        (
            outlet_pressure_this_stage_bara,
            outlet_stream,
        ) = calculate_outlet_pressure_and_stream(
            polytropic_efficiency=polytropic_efficiency,
            polytropic_head_joule_per_kg=polytropic_head_J_per_kg,
            inlet_stream=inlet_stream_compressor,
        )

        return CompressorTrainStageResultSingleTimeStep(
            inlet_stream=inlet_stream_compressor,  #  before RateModifier
            outlet_stream=outlet_stream,  #   after RateModifier
            inlet_stream_including_asv=inlet_stream_compressor_asv_corrected,
            outlet_stream_including_asv=FluidStream(
                thermo_system=outlet_stream.thermo_system,
                mass_rate_kg_per_h=inlet_stream_compressor_asv_corrected.mass_rate_kg_per_h,
            ),
            polytropic_head_kJ_per_kg=polytropic_head_J_per_kg / 1000,
            polytropic_efficiency=polytropic_efficiency,
            chart_area_flag=chart_area_flag,
            polytropic_enthalpy_change_kJ_per_kg=enthalpy_change_J_per_kg / 1000,
            power_megawatt=power_megawatt,
            point_is_valid=compressor_chart_head_and_efficiency_result.is_valid,
            polytropic_enthalpy_change_before_choke_kJ_per_kg=enthalpy_change_J_per_kg / 1000,
        )

    def evaluate_given_speed_and_target_discharge_pressure(
        self,
        inlet_stream_stage: FluidStream,
        target_discharge_pressure: float,
        speed: float | None = None,
    ) -> CompressorTrainStageResultSingleTimeStep:
        """
        Calculate the result of a single-speed compressor stage given a target discharge pressure.

        This method evaluates the compressor stage performance by iterating on the additional mass rate
        (ASV recirculation) to achieve the target discharge pressure. It ensures the solution is within
        the compressor's operational constraints.

        The process involves:
            1. Evaluating the stage without recirculation to check if the target pressure is met.
            2. Evaluating the stage with maximum recirculation to check if the target pressure is exceeded.
            3. Using a root-finding algorithm to determine the additional mass rate required to meet the target
               discharge pressure if the solution lies between the two bounds.

        Args:
            inlet_stream_stage (FluidStream): The inlet stream for the stage, containing pressure, temperature,
                and other fluid properties.
            target_discharge_pressure (float): The target discharge pressure for the stage in bar absolute [bara].
            speed (float)

        Returns:
            CompressorTrainStageResultSingleTimeStep: The result of the evaluation for the compressor stage,
            including the outlet stream and operational details.
        """
        # If no speed is defined for CompressorChart, use the minimum speed
        if isinstance(self.compressor_chart, CompressorChart) and speed is None:
            speed = self.compressor_chart.minimum_speed

        result_no_recirculation = self.evaluate(
            inlet_stream_stage=inlet_stream_stage,
            speed=speed,
            asv_additional_mass_rate=0,
        )

        # result_no_recirculation.inlet_stream.density_kg_per_m3 will have correct pressure and temperature
        # to find max mass rate, inlet_stream_stage will not
        maximum_rate = self.compressor_chart.maximum_rate_as_function_of_speed(speed)

        max_recirculation = max(
            maximum_rate * float(result_no_recirculation.inlet_stream.density)
            - inlet_stream_stage.mass_rate_kg_per_h
            - EPSILON,
            0,
        )
        result_max_recirculation = self.evaluate(
            inlet_stream_stage=inlet_stream_stage,
            asv_additional_mass_rate=max_recirculation,
            speed=speed,
        )
        if result_no_recirculation.discharge_pressure < target_discharge_pressure:
            return result_no_recirculation
        elif result_max_recirculation.discharge_pressure > target_discharge_pressure:
            return result_max_recirculation

        def _calculate_compressor_stage(
            additional_mass_rate: float,
        ) -> CompressorTrainStageResultSingleTimeStep:
            return self.evaluate(
                inlet_stream_stage=inlet_stream_stage,
                asv_additional_mass_rate=additional_mass_rate,
                speed=speed,
            )

        result_mass_rate = find_root(
            lower_bound=0,
            upper_bound=max_recirculation,
            func=lambda x: _calculate_compressor_stage(additional_mass_rate=x).discharge_pressure
            - target_discharge_pressure,
        )

        return _calculate_compressor_stage(result_mass_rate)

    def evaluate_given_target_pressure_ratio(
        self,
        inlet_stream: FluidStream,
        target_pressure_ratio: float,
        adjust_for_chart: bool = True,
    ) -> CompressorTrainStageResultSingleTimeStep:
        outlet_pressure = inlet_stream.pressure_bara * target_pressure_ratio

        inlet_stream = inlet_stream.create_stream_with_new_conditions(
            conditions=ProcessConditions(
                pressure_bara=inlet_stream.pressure_bara,
                temperature_kelvin=self.inlet_temperature_kelvin,
            )
        )

        # To avoid passing empty arrays down to the enthalpy calculation.
        if inlet_stream.mass_rate_kg_per_h > 0:
            polytropic_enthalpy_change_joule_per_kg, polytropic_efficiency = calculate_enthalpy_change_head_iteration(
                inlet_streams=inlet_stream,
                outlet_pressure=outlet_pressure,
                polytropic_efficiency_vs_rate_and_head_function=self.compressor_chart.efficiency_as_function_of_rate_and_head,
            )

            # Chart corrections to rate and head
            if adjust_for_chart:
                head_joule_per_kg = polytropic_enthalpy_change_joule_per_kg * polytropic_efficiency
                compressor_chart_result = self.compressor_chart.evaluate_capacity_and_extrapolate_below_minimum(
                    actual_volume_rates=inlet_stream.volumetric_rate,
                    heads=head_joule_per_kg,
                    extrapolate_heads_below_minimum=True,
                )
                asv_corrected_actual_rate_m3_per_hour = compressor_chart_result.asv_corrected_rates[0]
                choke_corrected_polytropic_head = compressor_chart_result.choke_corrected_heads[0]
                rate_has_recirc = compressor_chart_result.rate_has_recirc[0]
                pressure_is_choked = compressor_chart_result.pressure_is_choked[0]
                rate_exceeds_maximum = compressor_chart_result.rate_exceeds_maximum[0]
                head_exceeds_maximum = compressor_chart_result.head_exceeds_maximum[0]
                exceeds_capacity = compressor_chart_result.exceeds_capacity[0]

                polytropic_enthalpy_change_to_use_joule_per_kg = choke_corrected_polytropic_head / polytropic_efficiency
                mass_rate_to_use_kg_per_hour = asv_corrected_actual_rate_m3_per_hour * inlet_stream.density
            else:
                polytropic_enthalpy_change_to_use_joule_per_kg = polytropic_enthalpy_change_joule_per_kg
                mass_rate_to_use_kg_per_hour = inlet_stream.mass_rate_kg_per_h
                rate_has_recirc = False
                pressure_is_choked = False
                rate_exceeds_maximum = False
                head_exceeds_maximum = False
                exceeds_capacity = False

        else:
            polytropic_enthalpy_change_to_use_joule_per_kg = 0.0
            polytropic_enthalpy_change_joule_per_kg = 0.0
            polytropic_efficiency = np.nan
            mass_rate_to_use_kg_per_hour = inlet_stream.mass_rate_kg_per_h
            rate_has_recirc = False
            pressure_is_choked = False
            rate_exceeds_maximum = False
            head_exceeds_maximum = False
            exceeds_capacity = False

        outlet_stream = inlet_stream.create_stream_with_new_pressure_and_enthalpy_change(
            pressure_bara=outlet_pressure,
            enthalpy_change_joule_per_kg=polytropic_enthalpy_change_to_use_joule_per_kg,  # type: ignore[arg-type]
        )

        power_mw = (
            mass_rate_to_use_kg_per_hour
            * polytropic_enthalpy_change_to_use_joule_per_kg
            / UnitConstants.SECONDS_PER_HOUR
            * UnitConstants.WATT_TO_MEGAWATT
        )
        # Set power to nan for points where compressor capacity is exceeded
        if exceeds_capacity:
            power_mw = np.nan

        polytropic_enthalpy_change_kilo_joule_per_kg = polytropic_enthalpy_change_joule_per_kg * UnitConstants.TO_KILO

        if pressure_is_choked and rate_has_recirc:
            chart_area_flag = ChartAreaFlag.BELOW_MINIMUM_SPEED_AND_BELOW_MINIMUM_FLOW_RATE
        elif pressure_is_choked and rate_exceeds_maximum:
            chart_area_flag = ChartAreaFlag.BELOW_MINIMUM_SPEED_AND_ABOVE_MAXIMUM_FLOW_RATE
        elif rate_has_recirc:
            chart_area_flag = ChartAreaFlag.BELOW_MINIMUM_FLOW_RATE
        elif rate_exceeds_maximum:
            chart_area_flag = ChartAreaFlag.ABOVE_MAXIMUM_FLOW_RATE
        elif pressure_is_choked:
            chart_area_flag = ChartAreaFlag.BELOW_MINIMUM_SPEED
        elif head_exceeds_maximum:
            chart_area_flag = ChartAreaFlag.ABOVE_MAXIMUM_SPEED
        else:
            chart_area_flag = ChartAreaFlag.INTERNAL_POINT

        return CompressorTrainStageResultSingleTimeStep(
            inlet_stream=inlet_stream,
            outlet_stream=outlet_stream,
            inlet_stream_including_asv=FluidStream(
                thermo_system=inlet_stream.thermo_system,
                mass_rate_kg_per_h=mass_rate_to_use_kg_per_hour,
            ),
            outlet_stream_including_asv=FluidStream(
                thermo_system=outlet_stream.thermo_system,
                mass_rate_kg_per_h=mass_rate_to_use_kg_per_hour,
            ),
            power_megawatt=power_mw,  # type: ignore[arg-type]
            chart_area_flag=chart_area_flag,
            polytropic_enthalpy_change_kJ_per_kg=polytropic_enthalpy_change_to_use_joule_per_kg / 1000,  # type: ignore[arg-type]
            polytropic_enthalpy_change_before_choke_kJ_per_kg=polytropic_enthalpy_change_kilo_joule_per_kg,  # type: ignore[arg-type]
            polytropic_head_kJ_per_kg=(polytropic_enthalpy_change_to_use_joule_per_kg * polytropic_efficiency) / 1000,  # type: ignore[arg-type]
            polytropic_efficiency=polytropic_efficiency,  # type: ignore[arg-type]
            rate_has_recirculation=rate_has_recirc,
            rate_exceeds_maximum=rate_exceeds_maximum,
            pressure_is_choked=pressure_is_choked,
            head_exceeds_maximum=head_exceeds_maximum,
            # Assuming choking and ASV. Valid points are to the left and below the compressor chart.
            point_is_valid=~np.isnan(power_mw),  # type: ignore[arg-type] # power_mw is set to np.NaN if invalid step.
        )


class UndefinedCompressorStage(CompressorTrainStage):
    """A stage without a defined compressor chart is 'undefined'.

    Artifact of the 'Generic from Input' chart.
    """

    def __init__(
        self,
        polytropic_efficiency: float,
        compressor_chart: CompressorChart = None,  # Not in use. Not relevant when undefined.
        inlet_temperature_kelvin: float = 0.0,
        remove_liquid_after_cooling: bool = False,
        pressure_drop_ahead_of_stage: float | None = None,
    ):
        self.validate_predefined_chart(compressor_chart, polytropic_efficiency)
        self.validate_polytropic_efficiency(polytropic_efficiency)
        super().__init__(
            compressor_chart=compressor_chart,
            inlet_temperature_kelvin=inlet_temperature_kelvin,
            remove_liquid_after_cooling=remove_liquid_after_cooling,
            pressure_drop_ahead_of_stage=pressure_drop_ahead_of_stage,
        )
        self.polytropic_efficiency = polytropic_efficiency

    @staticmethod
    def validate_predefined_chart(compressor_chart, polytropic_efficiency):
        if compressor_chart is None and polytropic_efficiency is None:
            msg = "Stage with non-predefined compressor chart needs to have polytropic_efficiency."

            raise ProcessMissingVariableValidationException(message=str(msg))

    @staticmethod
    def validate_polytropic_efficiency(polytropic_efficiency):
        if not (0 < polytropic_efficiency <= 1):
            msg = f"polytropic_efficiency must be greater than 0 and less than or equal to 1. Invalid value: {polytropic_efficiency}"

            raise ProcessCompressorEfficiencyValidationException(message=str(msg))
