from copy import deepcopy
from typing import cast

from libecalc.common.errors.exceptions import IllegalStateException
from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl
from libecalc.common.fluid import FluidModel
from libecalc.common.fluid import FluidStream as FluidStreamDTO
from libecalc.common.logger import logger
from libecalc.domain.process.compressor.core.results import CompressorTrainResultSingleTimeStep
from libecalc.domain.process.compressor.core.train.base import CompressorTrainModel
from libecalc.domain.process.compressor.core.train.fluid import FluidStream
from libecalc.domain.process.compressor.core.train.train_evaluation_input import CompressorTrainEvaluationInput
from libecalc.domain.process.compressor.core.train.types import (
    FluidStreamObjectForMultipleStreams,
)
from libecalc.domain.process.compressor.core.train.utils.common import EPSILON
from libecalc.domain.process.compressor.core.train.utils.numeric_methods import (
    maximize_x_given_boolean_condition_function,
)
from libecalc.domain.process.compressor.dto import (
    VariableSpeedCompressorTrainMultipleStreamsAndPressures,
)
from libecalc.domain.process.core.results.compressor import (
    TargetPressureStatus,
)


class VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures(
    CompressorTrainModel[VariableSpeedCompressorTrainMultipleStreamsAndPressures]
):
    """An advanced model of a compressor train with variable speed, with the possibility of modelling additional
    streams going into or leaving the compressor train between the compressor train stages.

    In general, a compressor train is a series of compressors that are running with the same shaft, meaning they will
    always have the same speed. Given inlet conditions (composition, temperature, pressure, rate) for all ingoing
    streams, pressures and rates for outgoing streams (not counting the outlet at the final stage - it is what it
    becomes), and a shaft speed, the intermediate pressures (and temperature before cooling) between stages and the
    outlet pressure (and temperature) is given. To solve this for a given outlet pressure,
    one must iterate to find the speed.

    Streams:
    Models of the streams in the compressor train. See FluidStream
    Can be used with any number of streams going into or leaving the compressor train.
    The inlet of the first compressor stage must have an ingoing stream connected.

    Stages:
    Models of the compressor train stages. See CompressorTrainStage.
    For each stage, one must specify a compressor chart, an inlet temperature and whether to take out liquids before
    compression. In addition, one must specify the pressure drop from previous stage (may be 0).

    minimum_speed:
    The minimum speed of the compressor train shaft.
    If not specified it will be calculated from the given compressor charts for each of the stages

    maximum_speed:
    The maximum speed of the compressor train shaft.
    If not specified it will be calculated from the given compressor charts for each of the stages

    """

    def __init__(
        self,
        data_transfer_object: VariableSpeedCompressorTrainMultipleStreamsAndPressures,
        streams: list[FluidStreamObjectForMultipleStreams],
    ):
        logger.debug(
            f"Creating {type(self).__name__} with\n"
            f"n_stages: {len(data_transfer_object.stages)} and n_streams: {len(streams)}"
        )
        super().__init__(data_transfer_object=data_transfer_object)
        self.streams = streams
        self.number_of_compressor_streams = len(self.streams)

        self.inlet_stream_connected_to_stage: dict[int, list[int]] = {key: [] for key in range(len(self.stages))}
        self.outlet_stream_connected_to_stage: dict[int, list[int]] = {key: [] for key in range(len(self.stages))}
        for i, stream in enumerate(self.streams):
            if stream.is_inlet_stream:
                self.inlet_stream_connected_to_stage[stream.connected_to_stage_no].append(i)
            else:
                self.outlet_stream_connected_to_stage[stream.connected_to_stage_no].append(i)

        # in rare cases we can end up with trying to mix two streams with zero mass rate, and need the fluid from the
        # previous time step to recirculate. This will take care of that.
        self.fluid_to_recirculate_in_stage_when_inlet_rate_is_zero = [None] * len(self.stages)

    @staticmethod
    def _check_intermediate_pressure_stage_number_is_valid(
        _stage_number_intermediate_pressure: int,
        number_of_stages: int,
    ):
        """Fixme: Move to dto validation.
        Validate that the intermediate pressure stage number is within the allowed range.

        The intermediate pressure stage number specifies the stage for which the intermediate pressure is defined as the inlet pressure.
        This value must be greater than 0 (since stage 0 uses the suction pressure as its inlet) and less than the total number of stages.
        The method raises an exception if the value is out of bounds.

        Args:
            _stage_number_intermediate_pressure (int): The stage number for the intermediate pressure (zero-based).
            number_of_stages (int): The total number of stages in the compressor train.

        Raises:
            IllegalStateException: If the stage number is not within the valid range.
        """
        if _stage_number_intermediate_pressure is None or (
            _stage_number_intermediate_pressure < 1 or _stage_number_intermediate_pressure > number_of_stages - 1
        ):
            msg = (
                f"The stage number for the intermediate pressure must point to one of the intermediate stages and"
                f" can not be smaller than 1, and can not be larger than 1 minus the number of stages, but is"
                f" {_stage_number_intermediate_pressure} while the number of stages is {number_of_stages}."
                f" You should not end up here, please contact support"
            )
            logger.exception(msg)
            raise IllegalStateException(msg)

    def evaluate_given_constraints(
        self,
        constraints: CompressorTrainEvaluationInput,
    ) -> CompressorTrainResultSingleTimeStep:
        """
        Evaluate the compressor train for the given operating constraints.

        This method simulates the compressor train using the provided constraints, which may include stream rates,
        pressures, and shaft speed. It handles cases with and without intermediate pressure targets, determines the
        appropriate shaft speed if not specified, and applies pressure control if needed. The method ensures mass
        balance and returns an empty result if the configuration is invalid.

        Args:
            constraints (CompressorTrainEvaluationInput): The operating constraints, including pressures, stream rates,
                and optional speed or intermediate pressure.

        Returns:
            CompressorTrainResultSingleTimeStep: The result of the simulation, including stage results, inlet/outlet streams,
                speed, and pressure status. Returns an empty result if the configuration is invalid.
        """
        if not self.check_that_ingoing_streams_are_larger_than_or_equal_to_outgoing_streams(constraints.stream_rates):
            return CompressorTrainResultSingleTimeStep.create_empty(number_of_stages=len(self.stages))
        inlet_rates = [constraints.stream_rates[i] for (i, stream) in enumerate(self.streams) if stream.is_inlet_stream]
        # Enough with one positive ingoing stream. Compressors with possible zero rates will recirculate
        positive_ingoing_streams = list(filter(lambda x: x > 0, list(inlet_rates)))
        if not any(positive_ingoing_streams):
            return CompressorTrainResultSingleTimeStep.create_empty(number_of_stages=len(self.stages))
        else:
            if constraints.interstage_pressure is not None:
                self._check_intermediate_pressure_stage_number_is_valid(
                    _stage_number_intermediate_pressure=self.data_transfer_object.stage_number_interstage_pressure,
                    number_of_stages=len(self.stages),
                )
                return self.find_and_calculate_for_compressor_train_with_two_pressure_requirements(
                    stage_number_for_intermediate_pressure_target=self.data_transfer_object.stage_number_interstage_pressure,
                    constraints=constraints,
                    pressure_control_first_part=self.data_transfer_object.pressure_control_first_part,
                    pressure_control_last_part=self.data_transfer_object.pressure_control_last_part,
                )
            else:
                if constraints.speed is None:
                    speed = self.find_shaft_speed_given_constraints(
                        constraints=constraints,
                    )
                    train_result = self.calculate_compressor_train(
                        constraints=constraints.create_conditions_with_new_input(
                            new_speed=speed,
                        ),
                    )
                else:
                    speed = constraints.speed
                    train_result = self.calculate_compressor_train(
                        constraints=constraints,
                    )

                if train_result.target_pressure_status == TargetPressureStatus.TARGET_PRESSURES_MET:
                    # Solution found
                    return train_result
                elif train_result.target_pressure_status is TargetPressureStatus.BELOW_TARGET_DISCHARGE_PRESSURE:
                    # Not able to reach the requested discharge pressure at the given speed
                    # Return result (with failure) at given speed
                    return train_result
                elif self.pressure_control is None:
                    return train_result
                else:
                    train_result = self.evaluate_with_pressure_control_given_constraints(
                        constraints=constraints.create_conditions_with_new_input(
                            new_speed=speed,
                        )
                    )
                return train_result

    def check_that_ingoing_streams_are_larger_than_or_equal_to_outgoing_streams(
        self,
        std_rates_std_m3_per_day_per_stream: list[float],
    ) -> bool:
        """
        Check that, for each stage in the compressor train, the cumulative sum of ingoing streams up to that stage
        is at least as large as the cumulative sum of outgoing streams. This ensures mass balance, as a compressor
        train cannot generate fluid.

        Args:
            std_rates_std_m3_per_day_per_stream (list[float]): Standard rates [Sm3/day] for each stream in the compressor train.

        Returns:
            bool: True if, at every stage, the total ingoing volume is greater than or equal to the outgoing volume; False otherwise.
        """
        sum_of_ingoing_volume_up_to_current_stage_number = 0
        sum_of_outgoing_volume_up_to_current_stage_number = 0
        for stage_number, _ in enumerate(self.stages):
            sum_of_ingoing_volume_up_to_current_stage_number += sum(
                [
                    std_rates_std_m3_per_day_per_stream[inlet_stream_number]
                    for inlet_stream_number in self.inlet_stream_connected_to_stage[stage_number]
                ]
            )
            sum_of_outgoing_volume_up_to_current_stage_number += sum(
                [
                    std_rates_std_m3_per_day_per_stream[inlet_stream_number]
                    for inlet_stream_number in self.outlet_stream_connected_to_stage[stage_number]
                ]
            )
            if sum_of_outgoing_volume_up_to_current_stage_number > sum_of_ingoing_volume_up_to_current_stage_number:
                logger.warning(
                    f"For stage number {stage_number}, the sum of the outgoing streams exceeds the sum of the ingoing "
                    f"streams. Rates will be set to zero and time step not calculated."
                )
                return False

        return True

    def convert_to_rates_for_each_compressor_train_stages(self, rates_per_stream: list[float]) -> list[float]:
        """
        Convert stream rates to per-stage rates for the compressor train.

        This method takes the rates for each stream (either mass rates [kg/h] or standard rates [Sm3/day])
        and computes the corresponding rate for each stage in the compressor train, accounting for streams
        entering or leaving between stages.

        Args:
            rates_per_stream (list[float]): Rates for each stream in the compressor train, either as mass rates [kg/h]
                or standard rates [Sm3/day].

        Returns:
            list[float]: Rates for each stage in the compressor train, in the same units as the input.
        """
        stage_rates = []
        current_compressor_stage = 0
        previous_compressor_stage = 0
        for i, stream in enumerate(self.streams):
            # the next stage with an additional ingoing/outgoing stream.
            # current_compressor_stage is not necessarily previous_compressor_stage + 1, unless streams are entering
            # or leaving the train between all stages
            current_compressor_stage = stream.connected_to_stage_no
            if i == 0:
                stage_rates.append(rates_per_stream[i])
            else:
                # if no ingoing/outgoing streams between compressor train stages,
                # keep the rate coming out of the previous compressor train stage
                for _ in range(previous_compressor_stage, current_compressor_stage):
                    stage_rates.append(stage_rates[previous_compressor_stage])
                if stream.is_inlet_stream:  # if there is an extra ingoing rate, then add it
                    stage_rates[current_compressor_stage] += rates_per_stream[i]
                else:  # if there is an extra outgoing rate, then add it
                    stage_rates[current_compressor_stage] -= rates_per_stream[i]
            previous_compressor_stage = current_compressor_stage

        # if there are more stages after the last ingoing/outgoing stream keep the same rate
        for _ in range(current_compressor_stage + 1, len(self.stages)):
            stage_rates.append(stage_rates[previous_compressor_stage])

        return stage_rates

    def _get_max_std_rate_single_timestep(
        self,
        constraints: CompressorTrainEvaluationInput,
        allow_asv: bool = False,
    ) -> float:
        """
        Calculate the maximum standard volume rate [Sm3/day] for a single time step, given the current constraints.

        This method determines the highest possible rate for an ingoing stream that the compressor train can handle
        under the specified operating conditions. It iteratively increases the stream rate until the compressor train
        can no longer operate within valid limits, then returns the maximum valid rate found.

        Args:
            constraints (CompressorTrainEvaluationInput): The operating constraints, including which stream to maximuze.
            allow_asv (bool, optional): If True, allows anti-surge valve recirculation in the calculation. Defaults to False.

        Returns:
            float: The maximum standard volume rate in Sm3/day for the specified stream. Returns 0.0 if no valid rate is found.
        """
        stream_to_maximize_connected_to_stage_no = self.streams[constraints.stream_to_maximize].connected_to_stage_no

        # if it is not an ingoing stream --> currently no calculations done
        # Fixme: what should be returned? 0.0, NaN or something else?
        if not self.streams[constraints.stream_to_maximize].is_inlet_stream:
            return 0.0

        std_rates_std_m3_per_day_per_stream = constraints.stream_rates.copy()

        def _calculate_train_result(std_rate_for_stream: float) -> CompressorTrainResultSingleTimeStep:
            """Partial function of self.evaluate_given_constraints
            where we only pass std_rate_per_stream.
            """
            std_rates_std_m3_per_day_per_stream[constraints.stream_to_maximize] = std_rate_for_stream
            return self.evaluate_given_constraints(
                constraints=constraints.create_conditions_with_new_input(
                    new_rate=std_rates_std_m3_per_day_per_stream[0],
                    new_stream_rates=std_rates_std_m3_per_day_per_stream,
                ),
            )

        train_result = self.evaluate_given_constraints(
            constraints=constraints.create_conditions_with_new_input(
                new_speed=self.find_shaft_speed_given_constraints(
                    constraints=constraints,
                )
            )
        )
        if not train_result.is_valid:
            zero_stream_result = _calculate_train_result(std_rate_for_stream=EPSILON)
            if not zero_stream_result.is_valid:
                return 0.0
            else:
                return maximize_x_given_boolean_condition_function(
                    x_min=0.0,
                    x_max=float(constraints.stream_rates[constraints.stream_to_maximize]),
                    bool_func=lambda x: _calculate_train_result(std_rate_for_stream=x).is_valid,
                )
        else:
            max_rate_is_larger_than = std_rates_std_m3_per_day_per_stream[constraints.stream_to_maximize]
        while train_result.is_valid:
            max_rate_is_larger_than = train_result.stage_results[
                stream_to_maximize_connected_to_stage_no
            ].standard_rate_asv_corrected_sm3_per_day
            std_rates_std_m3_per_day_per_stream[constraints.stream_to_maximize] = max_rate_is_larger_than * 2
            train_result = self.evaluate_given_constraints(
                constraints=constraints.create_conditions_with_new_input(
                    new_speed=self.find_shaft_speed_given_constraints(
                        constraints=constraints.create_conditions_with_new_input(
                            new_rate=std_rates_std_m3_per_day_per_stream[0],
                            new_stream_rates=std_rates_std_m3_per_day_per_stream,
                        ),
                    ),
                    new_rate=std_rates_std_m3_per_day_per_stream[0],
                    new_stream_rates=std_rates_std_m3_per_day_per_stream,
                )
            )
        return maximize_x_given_boolean_condition_function(
            x_min=float(max_rate_is_larger_than),
            x_max=float(max_rate_is_larger_than * 2),
            bool_func=lambda x: _calculate_train_result(std_rate_for_stream=x).is_valid,
        )

    def calculate_compressor_train(
        self,
        constraints: CompressorTrainEvaluationInput,
        asv_rate_fraction: float = 0.0,
        asv_additional_mass_rate: float = 0.0,
    ) -> CompressorTrainResultSingleTimeStep:
        """
        Simulate the compressor train for the given inlet conditions, stream rates, and shaft speed.

        This method models the flow through each stage of the compressor train, accounting for multiple inlet and outlet
        streams, anti-surge valve recirculation, and possible subtrain configurations. It computes the resulting outlet
        stream, per-stage results (including conditions and power), and overall train performance.

        Typical usage scenarios:
            1. Standard train: self.streams[0] is the main inlet.
            2. First subtrain (with intermediate pressure target): self.streams[0] is the inlet.
            3. Last subtrain (after a split): self.streams[0] may be an entering or leaving stream, and the inlet fluid
               is set from the first subtrain.

        Args:
            constraints (CompressorTrainEvaluationInput): Pressures, stream rates, and speed for the simulation.
            asv_rate_fraction (float, optional): Fraction of anti-surge valve recirculation. Defaults to 0.0.
            asv_additional_mass_rate (float, optional): Additional mass rate for recirculation. Defaults to 0.0.

        Returns:
            CompressorTrainResultSingleTimeStep: Object containing inlet/outlet streams, per-stage results, speed,
            total power, and pressure status.
        """
        stage_results = []
        train_inlet_stream = inlet_stream = self.streams[0].fluid.get_fluid_stream(
            pressure_bara=constraints.suction_pressure,
            temperature_kelvin=self.stages[0].inlet_temperature_kelvin,
        )
        mass_rate_this_stage_kg_per_hour = inlet_stream.standard_rate_to_mass_rate(constraints.rate)
        mass_rate_previous_stage_kg_per_hour = 0
        previous_outlet_stream = None

        for stage_number, stage in enumerate(self.stages):
            if stage_number > 0:
                inlet_stream = previous_outlet_stream
                mass_rate_this_stage_kg_per_hour = mass_rate_previous_stage_kg_per_hour
            # take mass out before potential mixing with additional ingoing stream
            # assume that volume/mass is always taken out before additional volume/mass is potentially added, no matter
            # what order the streams are defined in the yaml file
            for stream_number in self.outlet_stream_connected_to_stage.get(stage_number):
                mass_rate_this_stage_kg_per_hour -= inlet_stream.standard_rate_to_mass_rate(
                    constraints.stream_rates[stream_number]
                )
            for stream_number in self.inlet_stream_connected_to_stage.get(stage_number):
                if stream_number > 0:
                    # Flash at outlet temperature or inlet temperature next stage? Must assume same temperature.
                    # Currently, using outlet temperature
                    additional_inlet_stream = self.streams[stream_number].fluid.get_fluid_stream(
                        pressure_bara=inlet_stream.pressure_bara,
                        temperature_kelvin=inlet_stream.temperature_kelvin,
                    )
                    mass_rate_additional_inlet_stream_kg_per_hour = additional_inlet_stream.standard_rate_to_mass_rate(
                        float(constraints.stream_rates[stream_number])
                    )
                    if (mass_rate_this_stage_kg_per_hour > 0) or (mass_rate_additional_inlet_stream_kg_per_hour > 0):
                        inlet_stream = additional_inlet_stream.mix_in_stream(
                            other_fluid_stream=inlet_stream,
                            self_mass_rate=mass_rate_additional_inlet_stream_kg_per_hour,
                            other_mass_rate=mass_rate_this_stage_kg_per_hour,
                            temperature_kelvin=additional_inlet_stream.temperature_kelvin,
                            pressure_bara=additional_inlet_stream.pressure_bara,
                        )
                    mass_rate_this_stage_kg_per_hour += mass_rate_additional_inlet_stream_kg_per_hour

            if mass_rate_this_stage_kg_per_hour == 0:
                fluid_to_recirculate = self.get_fluid_to_recirculate_in_stage_when_inlet_rate_is_zero(
                    stage_number=stage_number
                )
                if fluid_to_recirculate:
                    logger.warning(
                        f"For stage number {stage_number}, there is no fluid entering the stage at at this time step. "
                        f"The compressor is only recirculating fluid. Standard rates are "
                        f"{constraints.stream_rates}."
                    )
                    inlet_stream = fluid_to_recirculate
                else:
                    raise ValueError(
                        f"Trying to recirculate fluid in stage {stage_number} without defining which "
                        f"composition the fluid should have."
                    )

            stage_result = stage.evaluate(
                inlet_stream_stage=inlet_stream,
                mass_rate_kg_per_hour=mass_rate_this_stage_kg_per_hour,
                speed=constraints.speed,
                asv_rate_fraction=asv_rate_fraction,
                asv_additional_mass_rate=asv_additional_mass_rate,
            )
            stage_results.append(stage_result)

            # We need to recreate the domain object from the result object. This needs cleaning up.
            previous_outlet_stream = inlet_stream.set_new_pressure_and_temperature(
                new_pressure_bara=stage_result.outlet_stream.pressure_bara,
                new_temperature_kelvin=stage_result.outlet_stream.temperature_kelvin,
            )

            mass_rate_previous_stage_kg_per_hour = mass_rate_this_stage_kg_per_hour
            self.set_fluid_to_recirculate_in_stage_when_inlet_rate_is_zero(
                stage_number=stage_number, fluid_stream=inlet_stream
            )

        # check if target pressures are met
        target_pressure_status = self.check_target_pressures(
            constraints=constraints,
            results=stage_results,
        )

        return CompressorTrainResultSingleTimeStep(
            inlet_stream=FluidStreamDTO.from_fluid_domain_object(fluid_stream=train_inlet_stream),
            outlet_stream=FluidStreamDTO.from_fluid_domain_object(fluid_stream=previous_outlet_stream),
            stage_results=stage_results,
            speed=constraints.speed,
            above_maximum_power=sum([stage_result.power_megawatt for stage_result in stage_results])
            > self.maximum_power
            if self.maximum_power
            else False,
            target_pressure_status=target_pressure_status,
        )

    def _update_inlet_fluid_and_std_rates_for_last_subtrain(
        self,
        std_rates_std_m3_per_day_per_stream: list[float],
        inlet_pressure: float,
    ) -> tuple[FluidStream, list[float]]:
        """
        Updates the inlet fluid and standard rates for the last subtrain after splitting a compressor train.

        This method constructs the inlet fluid stream for the last subtrain by mixing the appropriate streams
        based on the provided standard rates and inlet pressure. It also computes the updated list of standard
        rates for the subtrain, ensuring that outgoing and additional ingoing streams are handled correctly.

        Args:
            std_rates_std_m3_per_day_per_stream (list[float]): Standard rates for each stream in the compressor train [Sm3/day].
            inlet_pressure (float): The inlet pressure for the subtrain [bara].

        Returns:
            tuple[FluidStream, list[float]]: A tuple containing:
                - The updated inlet fluid stream for the subtrain.
                - The updated list of standard rates for the subtrain.
        """
        # first make inlet stream from stream[0]
        inlet_stream = self.streams[0].fluid.get_fluid_stream(
            pressure_bara=inlet_pressure,
            temperature_kelvin=self.stages[0].inlet_temperature_kelvin,
        )
        inlet_std_rate = std_rates_std_m3_per_day_per_stream[0]
        inlet_mass_rate = inlet_stream.standard_rate_to_mass_rate(inlet_std_rate)

        # take mass out before potential mixing with additional ingoing stream
        # assume that volume/mass is always taken out before additional volume/mass is potentially added, no matter
        # what order the streams are defined in the yaml file
        for stream_number in self.outlet_stream_connected_to_stage.get(0):
            inlet_std_rate -= std_rates_std_m3_per_day_per_stream[stream_number]
        for stream_number in self.inlet_stream_connected_to_stage.get(0):
            if stream_number > 0:
                # mix stream from previous subtrain with incoming stream at first stage
                additional_inlet_stream = self.streams[stream_number].fluid.get_fluid_stream(
                    pressure_bara=inlet_pressure,
                    temperature_kelvin=self.stages[0].inlet_temperature_kelvin,
                )
                mass_rate_additional_inlet_stream = additional_inlet_stream.standard_rate_to_mass_rate(
                    std_rates_std_m3_per_day_per_stream[stream_number]
                )
                # mix streams to get inlet stream for first compressor stage
                # if rate is 0 don't try to mix,
                if (inlet_mass_rate > 0) or (mass_rate_additional_inlet_stream > 0):
                    inlet_stream = additional_inlet_stream.mix_in_stream(
                        other_fluid_stream=inlet_stream,
                        self_mass_rate=mass_rate_additional_inlet_stream,
                        other_mass_rate=inlet_mass_rate,
                        temperature_kelvin=additional_inlet_stream.temperature_kelvin,
                        pressure_bara=additional_inlet_stream.pressure_bara,
                    )
                inlet_std_rate += std_rates_std_m3_per_day_per_stream[stream_number]
                inlet_mass_rate = inlet_stream.standard_rate_to_mass_rate(inlet_std_rate)

        # update inlet fluid for the subtrain with new composition
        if inlet_mass_rate == 0:
            fluid_to_recirculate = self.get_fluid_to_recirculate_in_stage_when_inlet_rate_is_zero(stage_number=0)
            if fluid_to_recirculate:
                updated_inlet_fluid = fluid_to_recirculate
            else:
                raise ValueError("Trying to recirculate unknown fluid in compressor stage")
        else:
            updated_inlet_fluid = FluidStream(fluid_model=inlet_stream.fluid_model)
        updated_std_rates_std_m3_per_day_per_stream = [inlet_std_rate]
        updated_std_rates_std_m3_per_day_per_stream.extend(
            [
                std_rates_std_m3_per_day_per_stream[stream_number]
                for stream_number in range(self.number_of_compressor_streams)
                if stream_number
                not in set(self.outlet_stream_connected_to_stage.get(0) + self.inlet_stream_connected_to_stage.get(0))  # type: ignore[operator]
            ]
        )

        return updated_inlet_fluid, updated_std_rates_std_m3_per_day_per_stream

    def find_and_calculate_for_compressor_train_with_two_pressure_requirements(
        self,
        stage_number_for_intermediate_pressure_target: int,
        constraints: CompressorTrainEvaluationInput,
        pressure_control_first_part: FixedSpeedPressureControl,
        pressure_control_last_part: FixedSpeedPressureControl,
    ) -> CompressorTrainResultSingleTimeStep:
        """
        Calculates the compressor train performance when two pressure targets are specified: an intermediate (interstage)
        pressure and a final discharge pressure.

        The method splits the compressor train into two sub-trains at the specified stage. It determines the optimal shaft
        speed for each sub-train to meet their respective pressure targets, applies the appropriate pressure control
        strategies, and combines the results.

        Typical use case: part of the gas is taken out at an intermediate stage (e.g., for export or injection),
        requiring both an interstage and a final discharge pressure to be met.

        Args:
            stage_number_for_intermediate_pressure_target (int): The stage index at which the intermediate pressure target applies.
            constraints (CompressorTrainEvaluationInput): The operating constraints, including pressures and stream rates.
            pressure_control_first_part (FixedSpeedPressureControl): Pressure control strategy for the first sub-train.
            pressure_control_last_part (FixedSpeedPressureControl): Pressure control strategy for the second sub-train.

        Returns:
            CompressorTrainResultSingleTimeStep: The combined result of the two sub-trains, including stage results,
            inlet/outlet streams, speed, and pressure status.
        """
        # Split train into two and calculate minimum speed to reach required pressures
        compressor_train_first_part, compressor_train_last_part = split_train_on_stage_number(
            compressor_train=self,
            stage_number=stage_number_for_intermediate_pressure_target,
            pressure_control_first_part=pressure_control_first_part,
            pressure_control_last_part=pressure_control_last_part,
        )

        std_rates_first_part, std_rates_last_part = split_rates_on_stage_number(
            compressor_train=self,
            rates_per_stream=constraints.stream_rates,
            stage_number=stage_number_for_intermediate_pressure_target,
        )
        constraints_first_part = CompressorTrainEvaluationInput(
            suction_pressure=constraints.suction_pressure,
            discharge_pressure=constraints.interstage_pressure,
            rate=std_rates_first_part[0],
            stream_rates=std_rates_first_part,
        )
        constraints_last_part = CompressorTrainEvaluationInput(
            suction_pressure=constraints.interstage_pressure,
            discharge_pressure=constraints.discharge_pressure,
            rate=std_rates_last_part[0],
            stream_rates=std_rates_last_part,
        )

        compressor_train_first_part_optimal_speed = compressor_train_first_part.find_shaft_speed_given_constraints(
            constraints=constraints_first_part,
            lower_bound_for_speed=self.minimum_speed,  # Only search for a solution within the bounds of the
            upper_bound_for_speed=self.maximum_speed,  # original, complete compressor train
        )
        compressor_train_results_first_part_with_optimal_speed_result = (
            compressor_train_first_part.calculate_compressor_train(
                constraints=constraints_first_part.create_conditions_with_new_input(
                    new_speed=compressor_train_first_part_optimal_speed,
                )
            )
        )

        if self.data_transfer_object.calculate_max_rate:
            max_standard_rate_per_stream = [
                compressor_train_first_part.get_max_standard_rate(
                    constraints=CompressorTrainEvaluationInput(
                        rate=std_rates_first_part[0],
                        suction_pressure=constraints_first_part.suction_pressure,
                        discharge_pressure=constraints_first_part.discharge_pressure,
                        stream_rates=std_rates_first_part,
                        stream_to_maximize=stream_index,
                    ),
                )
                for stream_index, _ in enumerate(compressor_train_first_part.streams)
            ]
        else:
            max_standard_rate_per_stream = [float("nan")] * len(std_rates_first_part)

        # set self.inlet_fluid based on outlet_stream_first_part
        compressor_train_last_part.streams[0].fluid = FluidStream(  # filling the placeholder with the correct fluid
            fluid_model=FluidModel(
                composition=compressor_train_results_first_part_with_optimal_speed_result.stage_results[
                    -1
                ].outlet_stream.composition,
                eos_model=compressor_train_results_first_part_with_optimal_speed_result.stage_results[
                    -1
                ].outlet_stream.eos_model,
            )
        )

        compressor_train_last_part_optimal_speed = compressor_train_last_part.find_shaft_speed_given_constraints(
            constraints=constraints_last_part,
            lower_bound_for_speed=self.minimum_speed,
            upper_bound_for_speed=self.maximum_speed,
        )
        compressor_train_results_last_part_with_optimal_speed_result = (
            compressor_train_last_part.calculate_compressor_train(
                constraints=constraints_last_part.create_conditions_with_new_input(
                    new_speed=compressor_train_last_part_optimal_speed,
                )
            )
        )

        if self.data_transfer_object.calculate_max_rate:
            for stream_index, _ in enumerate(compressor_train_last_part.streams):
                if stream_index > 0:
                    max_standard_rate_per_stream.append(
                        compressor_train_first_part.get_max_standard_rate(
                            constraints=CompressorTrainEvaluationInput(
                                rate=std_rates_last_part[0],
                                suction_pressure=constraints_last_part.suction_pressure,
                                discharge_pressure=constraints_last_part.discharge_pressure,
                                stream_rates=std_rates_last_part,
                                stream_to_maximize=stream_index,
                            ),
                        )
                    )
        else:
            max_standard_rate_per_stream = max_standard_rate_per_stream + [float("nan")] * len(std_rates_last_part[1:])
        """
        Determine which of the first and last part will govern the speed to use
        Then run the last part as a single speed train with the speed chosen
        Fixme: Need to deliver the result in a proper format below.
        """
        if compressor_train_first_part_optimal_speed > compressor_train_last_part_optimal_speed:
            speed = compressor_train_first_part_optimal_speed
            compressor_train_results_last_part_with_pressure_control = (
                compressor_train_last_part.evaluate_with_pressure_control_given_constraints(
                    constraints=constraints_last_part.create_conditions_with_new_input(
                        new_speed=speed,
                    )
                )
            )
            compressor_train_results_to_return_first_part = (
                compressor_train_results_first_part_with_optimal_speed_result
            )
            compressor_train_results_to_return_last_part = compressor_train_results_last_part_with_pressure_control

        else:
            speed = compressor_train_last_part_optimal_speed
            compressor_train_results_first_part_with_pressure_control = (
                compressor_train_first_part.evaluate_with_pressure_control_given_constraints(
                    constraints=constraints_first_part.create_conditions_with_new_input(
                        new_speed=speed,
                    )
                )
            )
            compressor_train_results_to_return_first_part = compressor_train_results_first_part_with_pressure_control
            compressor_train_results_to_return_last_part = compressor_train_results_last_part_with_optimal_speed_result

        compressor_train_results_to_return_stage_results = list(
            compressor_train_results_to_return_first_part.stage_results
            + compressor_train_results_to_return_last_part.stage_results
        )

        for stage_number in range(len(self.stages)):
            self.set_fluid_to_recirculate_in_stage_when_inlet_rate_is_zero(
                stage_number=stage_number,
                fluid_stream=compressor_train_first_part.get_fluid_to_recirculate_in_stage_when_inlet_rate_is_zero(
                    stage_number=stage_number
                )
                if stage_number < stage_number_for_intermediate_pressure_target
                else compressor_train_last_part.get_fluid_to_recirculate_in_stage_when_inlet_rate_is_zero(
                    stage_number=stage_number - stage_number_for_intermediate_pressure_target
                ),
            )

        train_result = CompressorTrainResultSingleTimeStep(
            inlet_stream=compressor_train_results_to_return_first_part.inlet_stream,
            outlet_stream=compressor_train_results_to_return_last_part.outlet_stream,
            speed=speed,
            stage_results=compressor_train_results_to_return_stage_results,
            above_maximum_power=sum(
                [stage_result.power_megawatt for stage_result in compressor_train_results_to_return_stage_results]
            )
            > self.maximum_power
            if self.maximum_power
            else False,
            target_pressure_status=TargetPressureStatus.NOT_CALCULATED,
        )

        # check if target pressures are met
        target_pressure_status = self.check_target_pressures(
            constraints=constraints,
            results=train_result,
        )

        train_result.target_pressure_status = target_pressure_status

        return train_result

    def set_fluid_to_recirculate_in_stage_when_inlet_rate_is_zero(
        self, stage_number: int, fluid_stream: FluidStream
    ) -> None:
        """
        Store the fluid stream that passes through a specific compressor stage during the current calculation step.

        This method is used to keep track of the fluid composition for each stage, so that if the inlet rate becomes zero
        in a subsequent calculation step, the correct fluid can be recirculated.

        Args:
            stage_number (int): The zero-based index of the compressor stage.
            fluid_stream (FluidStream): The fluid stream to store for potential recirculation in the specified stage.
        """
        self.fluid_to_recirculate_in_stage_when_inlet_rate_is_zero[stage_number] = fluid_stream

    def get_fluid_to_recirculate_in_stage_when_inlet_rate_is_zero(self, stage_number: int) -> FluidStream:
        """
        Retrieve the fluid stream to be used for recirculation in a given compressor stage when the inlet rate is zero.

        This method returns the fluid that passed through the specified compressor stage during the previous calculation
        step. It is used to maintain the correct fluid composition and properties in cases where the inlet rate becomes zero
        and recirculation is required.

        Args:
            stage_number (int): The zero-based index of the compressor stage.

        Returns:
            FluidStream: The fluid stream to use for recirculation in the specified stage.
        """
        return self.fluid_to_recirculate_in_stage_when_inlet_rate_is_zero[stage_number]


def split_rates_on_stage_number(
    compressor_train: VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures,
    rates_per_stream: list[float],
    stage_number: int,
) -> tuple[list[float], list[float]]:
    """
    Splits the stream rates for a compressor train into two lists at the specified stage number.

    The first list contains rates for streams connected to stages before the split.
    The second list contains the rate at the split stage and rates for streams connected to stages at or after the split.

    Args:
        compressor_train: The compressor train instance containing stream and stage information.
        rates_per_stream: List of rates for each stream in the compressor train.
        stage_number: The stage index at which to split the rates (0-based).

    Returns:
        Tuple containing:
            - List of rates for the first part (before the split stage).
            - List of rates for the last part (from the split stage onward).
    """
    rates_first_part = [
        rates_per_stream[i]
        for i, stream in enumerate(compressor_train.streams)
        if stream.connected_to_stage_no < stage_number
    ]

    rates_last_part = [
        compressor_train.convert_to_rates_for_each_compressor_train_stages(rates_per_stream)[stage_number - 1]
    ]

    for i, stream in enumerate(compressor_train.streams):
        if stream.connected_to_stage_no >= stage_number:
            rates_last_part.append(rates_per_stream[i])

    return rates_first_part, rates_last_part


def split_train_on_stage_number(
    compressor_train: VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures,
    stage_number: int,
    pressure_control_first_part: FixedSpeedPressureControl | None = None,
    pressure_control_last_part: FixedSpeedPressureControl | None = None,
) -> tuple[
    VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures,
    VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures,
]:
    """
    Splits a variable speed compressor train into two sub-trains at the specified stage number.

    The first sub-train includes all stages before the split, and the second sub-train includes all stages from the split onward.
    Optionally, different pressure control strategies can be assigned to each sub-train.

    Args:
        compressor_train: The original variable speed compressor train to split.
        stage_number: The stage index at which to split the train (0-based).
        pressure_control_first_part: Optional pressure control for the first sub-train.
        pressure_control_last_part: Optional pressure control for the second sub-train.

    Returns:
        Tuple containing:
            - The first sub-train (stages before the split).
            - The second sub-train (stages from the split onward).
    """
    first_part_data_transfer_object = deepcopy(compressor_train.data_transfer_object)
    last_part_data_transfer_object = deepcopy(compressor_train.data_transfer_object)
    first_part_data_transfer_object.stages = first_part_data_transfer_object.stages[:stage_number]
    last_part_data_transfer_object.stages = last_part_data_transfer_object.stages[stage_number:]
    first_part_data_transfer_object.pressure_control = pressure_control_first_part
    last_part_data_transfer_object.pressure_control = pressure_control_last_part

    compressor_train_first_part = VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures(
        streams=[stream for stream in compressor_train.streams if stream.connected_to_stage_no < stage_number],
        data_transfer_object=cast(
            VariableSpeedCompressorTrainMultipleStreamsAndPressures, first_part_data_transfer_object
        ),
    )

    streams_last_part = [
        compressor_train.streams[compressor_train.inlet_stream_connected_to_stage.get(0)[0]]  # type: ignore[index]
    ]  # placeholder for stream coming out of first train, updated at runtime
    streams_last_part.extend(
        [
            FluidStreamObjectForMultipleStreams(
                fluid=stream.fluid,
                is_inlet_stream=stream.is_inlet_stream,
                connected_to_stage_no=stream.connected_to_stage_no - stage_number,
            )
            for stream in compressor_train.streams
            if stream.connected_to_stage_no >= stage_number
        ]
    )

    compressor_train_last_part = VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures(
        streams=streams_last_part,
        data_transfer_object=cast(
            VariableSpeedCompressorTrainMultipleStreamsAndPressures, last_part_data_transfer_object
        ),
    )

    for stage_no in range(len(compressor_train.stages)):
        if stage_no < stage_number:
            compressor_train_first_part.set_fluid_to_recirculate_in_stage_when_inlet_rate_is_zero(
                stage_number=stage_no,
                fluid_stream=compressor_train.get_fluid_to_recirculate_in_stage_when_inlet_rate_is_zero(stage_no),
            )
        else:
            compressor_train_last_part.set_fluid_to_recirculate_in_stage_when_inlet_rate_is_zero(
                stage_number=stage_no - stage_number,
                fluid_stream=compressor_train.get_fluid_to_recirculate_in_stage_when_inlet_rate_is_zero(stage_no),
            )

    return compressor_train_first_part, compressor_train_last_part
