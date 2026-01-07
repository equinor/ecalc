import numpy as np

from libecalc.common.errors.exceptions import IllegalStateException
from libecalc.common.fixed_speed_pressure_control import InterstagePressureControl
from libecalc.common.logger import logger
from libecalc.common.units import UnitConstants
from libecalc.domain.component_validation_error import (
    ProcessCompressorEfficiencyValidationException,
)
from libecalc.domain.process.compressor.core.results import CompressorTrainStageResultSingleTimeStep
from libecalc.domain.process.compressor.core.train.utils.common import (
    EPSILON,
    calculate_power_in_megawatt,
)
from libecalc.domain.process.compressor.core.train.utils.enthalpy_calculations import (
    calculate_enthalpy_change_head_iteration,
)
from libecalc.domain.process.compressor.core.train.utils.numeric_methods import find_root
from libecalc.domain.process.entities.process_units.compressor.compressor import Compressor
from libecalc.domain.process.entities.process_units.liquid_remover.liquid_remover import LiquidRemover
from libecalc.domain.process.entities.process_units.mixer.mixer import Mixer
from libecalc.domain.process.entities.process_units.pressure_modifier.pressure_modifier import (
    DifferentialPressureModifier,
)
from libecalc.domain.process.entities.process_units.rate_modifier.rate_modifier import RateModifier
from libecalc.domain.process.entities.process_units.splitter.splitter import Splitter
from libecalc.domain.process.entities.process_units.temperature_setter.temperature_setter import TemperatureSetter
from libecalc.domain.process.value_objects.chart.chart_area_flag import ChartAreaFlag
from libecalc.domain.process.value_objects.chart.compressor import (
    CompressorChart,
)
from libecalc.domain.process.value_objects.fluid_stream import FluidStream, ProcessConditions


class CompressorTrainStage:
    """A single stage in a compressor train.

    The stage is composed of a series of process units that modify the inlet stream before it enters the compressor.
    The process units are:
    - Splitter: Splits the inlet stream if required. One stream goes towards the compressor, the other(s) are taken out.
    - Mixer: Mixes the inlet stream with other streams if required.
    - TemperatureSetter: Cools the inlet stream to a required temperature. Often termed an intercooler.
    - LiquidRemover: Removes liquid from the inlet stream if required. Often termed a scrubber.
    - DifferentialPressureModifier: Chokes the inlet stream if a differential pressure control valve is defined.
    - RateModifier (add): Adds recirculation rate to the inlet stream if required. Mimics the ASV function.
    - Compressor: The compressor itself, defined by a CompressorChart.
    - RateModifier (remove): Removes the recirculation rate added before the compressor.

    Note: Used in both Single and Variable Speed compressor process modelling.
    """

    def __init__(
        self,
        compressor: Compressor,
        temperature_setter: TemperatureSetter,
        liquid_remover: LiquidRemover | None,
        rate_modifier: RateModifier,
        splitter: Splitter | None = None,
        mixer: Mixer | None = None,
        pressure_modifier: DifferentialPressureModifier | None = None,
        interstage_pressure_control: InterstagePressureControl | None = None,
    ):
        self.temperature_setter = temperature_setter
        self.liquid_remover = liquid_remover
        self.pressure_modifier = pressure_modifier
        self.rate_modifier = rate_modifier
        self.compressor = compressor
        self.splitter = splitter
        self.mixer = mixer
        self.interstage_pressure_control = interstage_pressure_control

    @property
    def remove_liquid_after_cooling(self) -> bool:
        return self.liquid_remover is not None

    @property
    def has_control_pressure(self):
        return self.interstage_pressure_control is not None

    @property
    def pressure_drop_ahead_of_stage(self) -> float:
        return self.pressure_modifier.differential_pressure if self.pressure_modifier is not None else 0.0

    @property
    def inlet_temperature_kelvin(self) -> float:
        return self.temperature_setter.required_temperature_kelvin

    def set_temperature(self, inlet_stream_stage: FluidStream) -> FluidStream:
        """Cool the inlet stream to the required temperature."""
        return self.temperature_setter.set_temperature(inlet_stream_stage)

    def remove_liquid(self, inlet_stream_stage: FluidStream) -> FluidStream:
        """Remove liquid from the inlet stream if required."""
        return self.liquid_remover.remove_liquid(inlet_stream_stage)

    def modify_pressure(self, inlet_stream_stage: FluidStream) -> FluidStream:
        """Choke the inlet stream if a differential pressure control valve is defined."""
        return self.pressure_modifier.modify_pressure(inlet_stream_stage)

    def add_recirculation_rate(
        self,
        inlet_stream_stage: FluidStream,
        speed: float,
        asv_rate_fraction: float | None = 0.0,
        asv_additional_mass_rate: float | None = 0.0,
    ) -> FluidStream:
        """Add recirculation rate to the inlet stream.

        Args:
            inlet_stream_stage (FluidStream): Inlet fluid stream conditions.
            speed (float): Compressor shaft speed.
            asv_rate_fraction (float): Fraction of available capacity for pressure control. Defaults to 0.0.
            asv_additional_mass_rate (float): Additional recirculated mass rate. Defaults to 0.0.

        Returns:
            FluidStream: Updated inlet stream.
        """
        has_asv_rate_fraction = asv_rate_fraction is not None and asv_rate_fraction > 0
        has_asv_additional_mass_rate = asv_additional_mass_rate is not None and asv_additional_mass_rate > 0
        if has_asv_rate_fraction and has_asv_additional_mass_rate:
            raise IllegalStateException("asv_rate_fraction and asv_additional_mass_rate cannot both be > 0")
        if asv_rate_fraction is not None and not (0.0 <= asv_rate_fraction <= 1.0):
            raise IllegalStateException("asv_rate_fraction must be in [0.0, 1.0]")

        actual_rate = inlet_stream_stage.volumetric_rate
        max_rate = self.compressor.compressor_chart.maximum_rate_as_function_of_speed(speed)
        min_rate = self.compressor.compressor_chart.minimum_rate_as_function_of_speed(speed)

        available_capacity = max(0, max_rate - actual_rate)
        additional_rate = max(
            min_rate - actual_rate,
            asv_rate_fraction * available_capacity if asv_rate_fraction else 0.0,
            asv_additional_mass_rate / inlet_stream_stage.density if asv_additional_mass_rate else 0.0,
        )

        self.rate_modifier.recirculation_mass_rate = additional_rate * inlet_stream_stage.density

        return self.rate_modifier.add_rate(inlet_stream_stage)

    def evaluate(
        self,
        inlet_stream_stage: FluidStream,
        speed: float,
        rates_out_of_splitter: list[float] | None = None,
        streams_in_to_mixer: list[FluidStream] | None = None,
        asv_rate_fraction: float | None = 0.0,
        asv_additional_mass_rate: float | None = 0.0,
    ) -> CompressorTrainStageResultSingleTimeStep:
        """Evaluates a compressor train stage given the conditions and rate of the inlet stream, and the speed
        of the shaft driving the compressor if given.

        Args:
            inlet_stream_stage (FluidStream): The conditions of the inlet fluid stream. If there are several inlet streams,
                the first one is the stage inlet stream, the others enter the stage at the Mixer.
            speed (float): The speed of the shaft driving the compressor
            rates_out_of_splitter (list[float] | None, optional): Additional rates to the Splitter if defined.
            streams_in_to_mixer (list[FluidStream] | None, optional): Additional streams to the Mixer if defined.
            asv_rate_fraction (float | None, optional): Fraction of the available capacity of the compressor to fill
                using some kind of pressure control (on the interval [0,1]). Defaults to 0.0.
            asv_additional_mass_rate (float | None, optional): Additional recirculated mass rate due to
                pressure control. Defaults to 0.0.

        Returns:
            CompressorTrainStageResultSingleTimeStep: The result of the evaluation for the compressor stage
        """
        # First the stream passes through the Splitter (if defined)
        if self.splitter is not None:
            self.splitter.rates_out_of_splitter = rates_out_of_splitter
            inlet_stream_after_splitter = self.split(
                inlet_stream_stage=inlet_stream_stage,
            )
        else:
            inlet_stream_after_splitter = inlet_stream_stage

        # Then the stream passes through the Mixer     (if defined)
        if self.mixer is not None:
            if streams_in_to_mixer is None:
                raise IllegalStateException("streams_in_to_mixer cannot be None when a mixer is defined")
            inlet_stream_after_mixer = self.mix(
                inlet_stream_stage=inlet_stream_after_splitter,
                streams_in_to_mixer=streams_in_to_mixer,
            )
        else:
            inlet_stream_after_mixer = inlet_stream_after_splitter

        # Then the stream passes through the PressureModifier (if defined),
        if self.pressure_modifier is not None:
            inlet_stream_after_pressure_modifier = self.modify_pressure(inlet_stream_after_mixer)
        else:
            inlet_stream_after_pressure_modifier = inlet_stream_after_mixer

        # Then the stream passes through the TemperatureSetter (which is always defined),
        inlet_stream_after_temperature_setter = self.set_temperature(inlet_stream_after_pressure_modifier)

        # Then the stream passes through the LiquidRemover (if defined),
        if self.liquid_remover is not None:
            inlet_stream_after_liquid_remover = self.remove_liquid(inlet_stream_after_temperature_setter)
        else:
            inlet_stream_after_liquid_remover = inlet_stream_after_temperature_setter

        inlet_stream_compressor = inlet_stream_after_liquid_remover

        # Then additional rate is added by the RateModifier (if defined),
        inlet_stream_compressor_including_asv = self.add_recirculation_rate(
            inlet_stream_stage=inlet_stream_compressor,
            speed=speed,
            asv_rate_fraction=asv_rate_fraction,
            asv_additional_mass_rate=asv_additional_mass_rate,
        )

        # Compressor
        if not (
            self.compressor.compressor_chart.minimum_speed <= speed <= self.compressor.compressor_chart.maximum_speed
        ):
            msg = f"Speed ({speed}) out of range ({self.compressor.compressor_chart.minimum_speed}-{self.compressor.compressor_chart.maximum_speed})."
            logger.exception(msg)
            raise IllegalStateException(msg)

        chart_area_flag, operational_point = self.compressor.find_chart_area_flag_and_operational_point(
            speed=speed,
            actual_rate_m3_per_h_including_asv=inlet_stream_compressor_including_asv.volumetric_rate,
            actual_rate_m3_per_h=inlet_stream_after_liquid_remover.volumetric_rate,
        )

        if operational_point.polytropic_efficiency == 0.0:
            raise ProcessCompressorEfficiencyValidationException("Efficiency from compressor chart is 0.")

        outlet_stream_compressor_including_asv = self.compress(
            inlet_stream_compressor=inlet_stream_compressor_including_asv,
            polytropic_efficiency=operational_point.polytropic_efficiency,
            polytropic_head_joule_per_kg=operational_point.polytropic_head_joule_per_kg,
        )
        outlet_stream_compressor = self.rate_modifier.remove_rate(outlet_stream_compressor_including_asv)

        enthalpy_change = operational_point.polytropic_head_joule_per_kg / operational_point.polytropic_efficiency
        power_megawatt = calculate_power_in_megawatt(
            enthalpy_change_joule_per_kg=enthalpy_change,
            mass_rate_kg_per_hour=inlet_stream_compressor_including_asv.mass_rate_kg_per_h,
        )

        return CompressorTrainStageResultSingleTimeStep(
            inlet_stream=inlet_stream_compressor,
            outlet_stream=outlet_stream_compressor,
            inlet_stream_including_asv=inlet_stream_compressor_including_asv,
            outlet_stream_including_asv=outlet_stream_compressor_including_asv,
            polytropic_head_kJ_per_kg=operational_point.polytropic_head_joule_per_kg / 1000,
            polytropic_efficiency=operational_point.polytropic_efficiency,
            chart_area_flag=chart_area_flag,
            polytropic_enthalpy_change_kJ_per_kg=enthalpy_change / 1000,
            power_megawatt=power_megawatt,
            point_is_valid=operational_point.is_valid,
            polytropic_enthalpy_change_before_choke_kJ_per_kg=enthalpy_change / 1000,
        )

    def split(
        self,
        inlet_stream_stage: FluidStream,
    ) -> FluidStream:
        """Split the inlet stream into many streams. One stream goes to the compressor stage. The other(s) are taken out.
        In the future, the additional streams could be used for other purposes, but today they are just dropped completely.

        Args:
            inlet_stream_stage (FluidStream): The inlet stream for the stage.

        Returns:
            FluidStream: The stream going to the compressor stage.
        """
        assert self.splitter is not None
        split_streams = self.splitter.split_stream(
            stream=inlet_stream_stage,
        )
        return split_streams[-1]  # The last stream goes to the compressor stage

    def mix(
        self,
        inlet_stream_stage: FluidStream,
        streams_in_to_mixer: list[FluidStream],
        prefer_first_stream: bool = True,
    ) -> FluidStream:
        """Mix the inlet stream with additional streams.

        There is a special case where all streams have zero mass flow. In that case, if prefer_first_stream is True,
        the properties of the first stream (inlet_stream_stage) are returned. This is useful for scenarios where a
        compressor stage at some point in time recirculates all the fluid it needs to operate - there is no net rate
        going through the stage - but a fluid model is still needed to do the compressor calculations.

        Args:
            inlet_stream_stage (FluidStream): The inlet stream for the stage.
            streams_in_to_mixer (list[FluidStream]): Additional streams to mix with the inlet stream.
            prefer_first_stream (bool): Whether to prefer the properties of the first stream when mixing streams
                                        with zero mass flow. Defaults to True. (Which fluid to recirculate)

        Returns:
            FluidStream: The mixed stream.
        """
        assert self.mixer is not None
        assert streams_in_to_mixer is not None
        if self.mixer.number_of_inputs != len(streams_in_to_mixer) + 1:
            raise IllegalStateException(
                f"Number of additional rates to Splitter ({len(streams_in_to_mixer)}) "
                f"does not match number of Splitter outputs ({self.splitter.number_of_inputs})."
            )

        all_streams_to_mixer = [inlet_stream_stage] + streams_in_to_mixer
        if sum(s.mass_rate_kg_per_h for s in all_streams_to_mixer) == 0:
            if prefer_first_stream:
                return inlet_stream_stage

        return self.mixer.mix_streams(
            streams=all_streams_to_mixer,
        )

    def compress(
        self,
        inlet_stream_compressor: FluidStream,
        polytropic_efficiency: float,
        polytropic_head_joule_per_kg: float,
    ) -> FluidStream:
        return self.compressor.compress(
            polytropic_efficiency=polytropic_efficiency,
            polytropic_head_joule_per_kg=polytropic_head_joule_per_kg,
            inlet_stream=inlet_stream_compressor,
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
        if isinstance(self.compressor.compressor_chart, CompressorChart) and speed is None:
            speed = self.compressor.compressor_chart.minimum_speed

        result_no_recirculation = self.evaluate(
            inlet_stream_stage=inlet_stream_stage,
            speed=speed,
            asv_additional_mass_rate=0,
        )

        # result_no_recirculation.inlet_stream.density_kg_per_m3 will have correct pressure and temperature
        # to find max mass rate, inlet_stream_stage will not
        maximum_rate = self.compressor.compressor_chart.maximum_rate_as_function_of_speed(speed)

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
                polytropic_efficiency_vs_rate_and_head_function=self.compressor.compressor_chart.efficiency_as_function_of_rate_and_head,
            )

            # Chart corrections to rate and head
            if adjust_for_chart:
                head_joule_per_kg = polytropic_enthalpy_change_joule_per_kg * polytropic_efficiency
                compressor_chart_result = (
                    self.compressor.compressor_chart.evaluate_capacity_and_extrapolate_below_minimum(
                        actual_volume_rates=inlet_stream.volumetric_rate,
                        heads=head_joule_per_kg,
                        extrapolate_heads_below_minimum=True,
                    )
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
