from copy import deepcopy
from typing import cast

from libecalc.common.errors.exceptions import IllegalStateException
from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl
from libecalc.common.fluid import FluidModel
from libecalc.common.fluid import FluidStream as FluidStreamDTO
from libecalc.common.logger import logger
from libecalc.common.serializable_chart import SingleSpeedChartDTO
from libecalc.common.units import UnitConstants
from libecalc.domain.process.compressor.core.results import CompressorTrainResultSingleTimeStep
from libecalc.domain.process.compressor.core.train.base import CompressorTrainModel
from libecalc.domain.process.compressor.core.train.fluid import FluidStream
from libecalc.domain.process.compressor.core.train.single_speed_compressor_train_common_shaft import (
    SingleSpeedCompressorTrainCommonShaft,
)
from libecalc.domain.process.compressor.core.train.stage import CompressorTrainStage
from libecalc.domain.process.compressor.core.train.types import (
    FluidStreamObjectForMultipleStreams,
)
from libecalc.domain.process.compressor.core.train.utils.common import EPSILON
from libecalc.domain.process.compressor.core.train.utils.numeric_methods import (
    find_root,
    maximize_x_given_boolean_condition_function,
)
from libecalc.domain.process.compressor.core.train.utils.variable_speed_compressor_train_common_shaft import (
    get_single_speed_equivalent,
)
from libecalc.domain.process.compressor.dto import (
    CompressorStage,
    SingleSpeedCompressorTrain,
    VariableSpeedCompressorTrainMultipleStreamsAndPressures,
)
from libecalc.domain.process.core.results.compressor import (
    TargetPressureStatus,
)
from libecalc.domain.process.core.stream import ProcessConditions
from libecalc.domain.process.core.stream.mixing import SimplifiedStreamMixing
from libecalc.domain.process.core.stream.stream import Stream
from libecalc.domain.process.core.stream.thermo_system import NeqSimThermoSystem


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
        self.fluid = streams[0].fluid
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
        self.stream_to_recirculate_in_stage_when_inlet_rate_is_zero = [None] * len(self.stages)
        self._target_stream_rates = None
        self._target_stream_to_maximize = 0  # default to inlet stream

    def get_target_stream_rate(self, stream_no: int) -> float | None:
        """Get the target stream rate for a specific stream in the compressor train.

        Args:
            stream_no (int): The index of the stream in the compressor train.

        Returns:
            float | None: The target stream rate for the specified stream, or None if not set.
        """
        if self._target_stream_rates is not None:
            return self._target_stream_rates[stream_no]
        else:
            return None

    @property
    def target_stream_rates(self) -> list[float]:
        return self._target_stream_rates

    @target_stream_rates.setter
    def target_stream_rates(self, value):
        self._target_stream_rates = value

    @property
    def target_stream_to_maximize(self) -> int:
        return self._target_stream_to_maximize

    @target_stream_to_maximize.setter
    def target_stream_to_maximize(self, value):
        self._target_stream_to_maximize = value

    @staticmethod
    def _check_intermediate_pressure_stage_number_is_valid(
        _stage_number_intermediate_pressure: int,
        number_of_stages: int,
    ):
        """Fixme: Move to dto validation.

        The stage number intermediate pressure is the stage that the intermediate pressure defines the inlet
        pressure for. Thus, this number must be larger than 0 (first stage (stage 0) has ps as inlet pressure),
        and less than the number of stages (it may be the inlet pressure of the last stage as this has a defined
        discharge pressure, but undefined inlet pressure. Zero indexed, i.e. first stage = stage_0 and
        last stage = stage_n-1, n is the number of stages
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

    def _set_evaluate_constraints(
        self,
        rate: list[float],
        suction_pressure: float,
        discharge_pressure: float,
        stream_to_maximize: int = 0,
        intermediate_pressure: float | None = None,
        speed: float | None = None,
    ):
        """
        Sets the evaluation constraints for the compressor train. Typically, rates and pressures that needs to be
        met when evaluation is performed.

        Args:
            rate (float | list[float]): Rate in [Sm3/day].
            suction_pressure (float): Suction pressure in [bara].
            discharge_pressure (float): Discharge pressure in [bara].
            intermediate_pressure (float | None): Intermediate pressure in [bara], or None.
        """
        self.target_suction_pressure = suction_pressure
        self.target_discharge_pressure = discharge_pressure
        self.target_intermediate_pressure = intermediate_pressure
        self.target_inlet_rate = rate[0]
        self.target_stream_rates = rate
        self.target_stream_to_maximize = stream_to_maximize
        return self

    def _evaluate(
        self,
    ) -> CompressorTrainResultSingleTimeStep:
        self.check_that_ingoing_streams_are_larger_than_or_equal_to_outgoing_streams()
        inlet_rates = [self.target_stream_rates[i] for (i, stream) in enumerate(self.streams) if stream.is_inlet_stream]
        # Enough with one positive ingoing stream. Compressors with possible zero rates will recirculate
        positive_ingoing_streams = list(filter(lambda x: x > 0, list(inlet_rates)))
        if not any(positive_ingoing_streams):
            return CompressorTrainResultSingleTimeStep.create_empty(number_of_stages=len(self.stages))
        else:
            process_conditions = ProcessConditions(
                temperature_kelvin=self.stages[0].inlet_temperature_kelvin,
                pressure_bara=self.target_suction_pressure,
            )
            train_inlet_stream = Stream.from_standard_rate(
                thermo_system=NeqSimThermoSystem(
                    composition=self.streams[0].fluid.fluid_model.composition,
                    eos_model=self.streams[0].fluid.fluid_model.eos_model,
                    conditions=process_conditions,
                ),
                standard_rate=self.target_inlet_rate,
            )
            if self.target_intermediate_pressure is not None:
                self._check_intermediate_pressure_stage_number_is_valid(
                    _stage_number_intermediate_pressure=self.data_transfer_object.stage_number_interstage_pressure,
                    number_of_stages=len(self.stages),
                )
                return self.find_and_calculate_for_compressor_train_with_two_pressure_requirements(
                    stage_number_for_intermediate_pressure_target=self.data_transfer_object.stage_number_interstage_pressure,
                    train_inlet_stream=train_inlet_stream,
                    pressure_control_first_part=self.data_transfer_object.pressure_control_first_part,
                    pressure_control_last_part=self.data_transfer_object.pressure_control_last_part,
                )
            else:
                return self.evaluate_compressor_train_given_train_inlet_stream_and_target_discharge_pressure(
                    train_inlet_stream=train_inlet_stream,
                )

    def check_that_ingoing_streams_are_larger_than_or_equal_to_outgoing_streams(
        self,
    ) -> None:
        """Check that, for each stage in the compressor train, the cumulative sum of ingoing streams up to that stage
        is greater than or equal to the cumulative sum of outgoing streams up to that stage. This ensures mass balance,
        as a compressor train cannot generate fluid.

        If the outgoing streams exceed the ingoing streams at any stage, all rates are set to zero and the time step is not calculated.
        """
        sum_of_ingoing_volume_up_to_current_stage_number = 0
        sum_of_outgoing_volume_up_to_current_stage_number = 0
        for stage_number, _ in enumerate(self.stages):
            sum_of_ingoing_volume_up_to_current_stage_number += sum(
                [
                    self.target_stream_rates[inlet_stream_number]
                    for inlet_stream_number in self.inlet_stream_connected_to_stage[stage_number]
                ]
            )
            sum_of_outgoing_volume_up_to_current_stage_number += sum(
                [
                    self.target_stream_rates[inlet_stream_number]
                    for inlet_stream_number in self.outlet_stream_connected_to_stage[stage_number]
                ]
            )
            if sum_of_outgoing_volume_up_to_current_stage_number > sum_of_ingoing_volume_up_to_current_stage_number:
                logger.warning(
                    f"For stage number {stage_number}, the sum of the outgoing streams exceeds the sum of the ingoing "
                    f"streams. Rates will be set to zero and time step not calculated."
                )
                self.target_inlet_rate = 0
                self.target_stream_rates = [0] * len(self.target_stream_rates)

    def convert_to_rates_for_each_compressor_train_stages(self, rates_per_stream: list[float]) -> list[float]:
        """The function takes rates for each stream in the compressor train, and converts it to a rate
        for each stage in the compressor train.

        The function will always be called with a 1D numpy array as input (for one time step)

        :param rates_per_stream: mass rates [kg/h] or standard rates [Sm3/day] for each stream in the compressor train
        :returns: rates for each stage in the compressor train

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

    def evaluate_compressor_train_given_train_inlet_stream_and_target_discharge_pressure(
        self,
        train_inlet_stream: Stream,
        lower_bound_for_speed: float | None = None,
        upper_bound_for_speed: float | None = None,
    ) -> CompressorTrainResultSingleTimeStep:
        """
        Run the compressor train forward model with given inlet conditions and iterate on shaft speed until the discharge
        pressure matches the requested target discharge pressure.

        Args:
            lower_bound_for_speed (float | None): Optional lower boundary for shaft rotational speed. If not defined, uses the minimum speed from the compressor chart.
            upper_bound_for_speed (float | None): Optional upper boundary for shaft rotational speed. If not defined, uses the maximum speed from the compressor chart.

        Returns:
            CompressorTrainResultSingleTimeStep: The result of the compressor train calculations for the given conditions.
        """
        minimum_speed = lower_bound_for_speed if lower_bound_for_speed else self.minimum_speed
        maximum_speed = upper_bound_for_speed if upper_bound_for_speed else self.maximum_speed

        def _evaluate_compressor_train_given_train_inlet_stream_and_speed(
            _speed: float,
        ) -> CompressorTrainResultSingleTimeStep:
            return self.evaluate_compressor_train_given_train_inlet_stream_and_speed(
                train_inlet_stream=train_inlet_stream,
                speed=_speed,
            )

        train_result_for_minimum_speed = _evaluate_compressor_train_given_train_inlet_stream_and_speed(
            _speed=minimum_speed
        )
        train_result_for_maximum_speed = _evaluate_compressor_train_given_train_inlet_stream_and_speed(
            _speed=maximum_speed
        )

        if not train_result_for_maximum_speed.within_capacity:
            # will not find valid result - the rate is above maximum rate, return invalid results at maximum speed
            return train_result_for_maximum_speed
        if not train_result_for_minimum_speed.within_capacity:
            # rate is above maximum rate for minimum speed. Find the lowest minimum speed which gives a valid result
            minimum_speed = -maximize_x_given_boolean_condition_function(
                x_min=-self.maximum_speed,
                x_max=-self.minimum_speed,
                bool_func=lambda x: _evaluate_compressor_train_given_train_inlet_stream_and_speed(
                    _speed=-x
                ).within_capacity,
            )
            train_result_for_minimum_speed = _evaluate_compressor_train_given_train_inlet_stream_and_speed(
                _speed=minimum_speed
            )

        # Solution 1, iterate on speed until target discharge pressure is found
        if (
            train_result_for_minimum_speed.discharge_pressure
            <= self.target_discharge_pressure
            <= train_result_for_maximum_speed.discharge_pressure
        ):
            speed = find_root(
                lower_bound=minimum_speed,
                upper_bound=maximum_speed,
                func=lambda x: _evaluate_compressor_train_given_train_inlet_stream_and_speed(
                    _speed=x
                ).discharge_pressure
                - self.target_discharge_pressure,
            )

            return _evaluate_compressor_train_given_train_inlet_stream_and_speed(_speed=speed)

        # Solution 2, try pressure control mechanism or target pressure is too low:
        elif self.target_discharge_pressure < train_result_for_minimum_speed.discharge_pressure:
            if self.pressure_control:
                return self.evaluate_compressor_train_using_pressure_control_at_given_speed(
                    speed=minimum_speed,
                    train_inlet_stream=train_inlet_stream,
                )
            else:
                return train_result_for_minimum_speed
        # Solution 3, target discharge pressure is too high
        else:
            return train_result_for_maximum_speed

    def _get_max_std_rate_single_timestep(
        self,
        train_inlet_stream: Stream,
    ) -> float:
        """NB: Constraining to calculating maximum_rate for ingoing streams for now - the need is to figure out how much rate
        can be added.

        """
        keep_target_stream_rate = self.target_stream_rates[
            self.target_stream_to_maximize
        ]  # set it back to correct value after calculation
        # if it is not an ingoing stream --> currently no calculations done
        # Fixme: what should be returned? 0.0, NaN or something else?
        if not self.streams[self.target_stream_to_maximize].is_inlet_stream:
            return 0.0

        def _calculate_train_result_with_changed_stream_rate(
            std_rate_for_stream: float,
        ) -> CompressorTrainResultSingleTimeStep:
            """Partial function of self.calculate_compressor_train_given_rate_ps_speed
            where we only pass std_rate_per_stream and speed.
            """
            if self.target_stream_to_maximize == 0:
                tmp_train_inlet_stream = Stream.from_standard_rate(
                    standard_rate=std_rate_for_stream,
                    thermo_system=train_inlet_stream.thermo_system,
                )
            else:
                tmp_train_inlet_stream = train_inlet_stream
                self.target_stream_rates[self.target_stream_to_maximize] = std_rate_for_stream

            result = self.evaluate_compressor_train_given_train_inlet_stream_and_target_discharge_pressure(
                train_inlet_stream=tmp_train_inlet_stream,
            )

            if self.target_stream_to_maximize > 0:
                self.target_stream_rates[self.target_stream_to_maximize] = keep_target_stream_rate

            return result

        train_result = self.evaluate_compressor_train_given_train_inlet_stream_and_target_discharge_pressure(
            train_inlet_stream=train_inlet_stream,
        )
        if not train_result.is_valid:
            zero_stream_result = _calculate_train_result_with_changed_stream_rate(std_rate_for_stream=EPSILON)
            if not zero_stream_result.is_valid:
                return 0.0
            else:
                return maximize_x_given_boolean_condition_function(
                    x_min=0.0,
                    x_max=float(self.target_stream_rates[self.target_stream_to_maximize]),
                    bool_func=lambda x: _calculate_train_result_with_changed_stream_rate(
                        std_rate_for_stream=x
                    ).is_valid,
                )
        else:
            max_rate_is_larger_than = self.target_stream_rates[self.target_stream_to_maximize]
            while train_result.is_valid:
                max_rate_is_larger_than *= 2
                train_result = _calculate_train_result_with_changed_stream_rate(
                    std_rate_for_stream=max_rate_is_larger_than
                )
            return maximize_x_given_boolean_condition_function(
                x_min=float(max_rate_is_larger_than / 2),
                x_max=float(max_rate_is_larger_than),
                bool_func=lambda x: _calculate_train_result_with_changed_stream_rate(std_rate_for_stream=x).is_valid,
            )

    def _update_stream_between_stages(
        self,
        stage_number: int,
        stage_outlet_stream: Stream,
    ) -> Stream:
        """Update the inlet stream for the next stage in the compressor train.

        Args:
            stage_number (int): The stage number to update.
            train_inlet_stream (Stream): The inlet stream for the compressor train.

        Returns:
            Stream: The updated inlet stream for the next stage.
        """
        stage_inlet_stream = stage_outlet_stream
        # Potential streams leaving the compressor train between stages
        for stream_number in self.outlet_stream_connected_to_stage.get(stage_number):
            stage_inlet_stream = Stream.from_standard_rate(
                thermo_system=stage_inlet_stream.thermo_system,
                standard_rate=stage_inlet_stream.standard_rate - self.target_stream_rates[stream_number],
            )
        # Potential streams (other than the train inlet stream) entering the compressor train between stages
        for stream_number in self.inlet_stream_connected_to_stage.get(stage_number):
            if stream_number > 0:
                # Flash at outlet temperature or inlet temperature next stage? Must assume same temperature.
                # Currently, using outlet temperature
                additional_stage_inlet_stream = Stream.from_standard_rate(
                    thermo_system=NeqSimThermoSystem(
                        composition=self.streams[stream_number].fluid.fluid_model.composition,
                        eos_model=self.streams[stream_number].fluid.fluid_model.eos_model,
                        conditions=ProcessConditions(
                            temperature_kelvin=stage_inlet_stream.temperature_kelvin,
                            pressure_bara=stage_inlet_stream.pressure_bara,
                        ),
                    ),
                    standard_rate=self.target_stream_rates[stream_number],
                )
                if additional_stage_inlet_stream.mass_rate > 0:
                    stage_inlet_stream = SimplifiedStreamMixing().mix_streams(
                        streams=[stage_inlet_stream, additional_stage_inlet_stream]
                    )

        if stage_inlet_stream.mass_rate == 0:
            stage_inlet_stream = self.get_stream_to_recirculate_in_stage_when_inlet_rate_is_zero(
                stage_number=stage_number
            )
            if stage_inlet_stream is not None:
                logger.warning(
                    f"For stage number {stage_number}, there is no fluid entering the stage at at this time step. "
                    f"The compressor is only recirculating fluid. Standard rates are "
                    f"{self.target_stream_rates}."
                )
            else:
                raise ValueError(
                    f"Trying to recirculate fluid in stage {stage_number} without defining which "
                    f"composition the fluid should have."
                )
        return stage_inlet_stream

    def evaluate_compressor_train_given_train_inlet_stream_and_speed(
        self,
        train_inlet_stream: float,
        speed: float,
        asv_rate_fraction: float = 0.0,
        asv_additional_mass_rate: float = 0.0,
    ) -> CompressorTrainResultSingleTimeStep:
        """Calculate the compressor train result given inlet conditions and shaft speed.

        Returns the outlet stream from the final compressor stage (which may differ from the inlet stream due to multiple inlet streams)
        and results including conditions and calculations for each stage and total power.

        This function can be used in three scenarios:
        1) For a compressor train without an intermediate pressure target: `self.streams[0]` is used as the inlet stream.
        2) As the first subtrain in a train with an intermediate pressure target: `self.streams[0]` is the inlet stream.
        3) As the last subtrain in a train with an intermediate pressure target: `self.streams[0]` may be a stream entering/leaving the train,
           while `self.inlet_fluid` describes the fluid from the first subtrain.

        Args:
            train_inlet_stream (Stream): The inlet stream of the compressor train.
            speed (float): Shaft speed in rpm.
            asv_rate_fraction (float, optional): Fraction of anti-surge valve recirculation. Defaults to 0.0.
            asv_additional_mass_rate (float, optional): Additional mass rate for anti-surge valve. Defaults to 0.0.

        Returns:
            CompressorTrainResultSingleTimeStep: Result object containing stage results, inlet/outlet streams, speed, and power information.
        """
        stage_results = []
        stage_outlet_stream = train_inlet_stream

        for stage_number, stage in enumerate(self.stages):
            stage_inlet_stream = self._update_stream_between_stages(
                stage_number=stage_number,
                stage_outlet_stream=stage_outlet_stream,
            )
            stage_result = stage.evaluate(
                inlet_stream_stage=stage_inlet_stream,
                speed=speed,
                asv_rate_fraction=asv_rate_fraction,
                asv_additional_mass_rate=asv_additional_mass_rate,
            )
            stage_results.append(stage_result)

            # We need to recreate the domain object from the result object. This needs cleaning up.
            stage_outlet_stream = train_inlet_stream.create_stream_with_new_conditions(
                conditions=ProcessConditions(
                    pressure_bara=stage_result.outlet_stream.pressure_bara,
                    temperature_kelvin=stage_result.outlet_stream.temperature_kelvin,
                )
            )
            self.set_stream_to_recirculate_in_stage_when_inlet_rate_is_zero(
                stage_number=stage_number, stream=stage_inlet_stream
            )

        # check if target pressures are met
        target_pressure_status = self.check_target_pressures(
            calculated_suction_pressure=train_inlet_stream.pressure_bara,
            calculated_discharge_pressure=stage_outlet_stream.pressure_bara,
        )

        return CompressorTrainResultSingleTimeStep(
            inlet_stream=FluidStreamDTO.from_fluid_process_object(fluid_stream=train_inlet_stream),
            outlet_stream=FluidStreamDTO.from_fluid_process_object(fluid_stream=stage_outlet_stream),
            stage_results=stage_results,
            speed=speed,
            above_maximum_power=sum([stage_result.power_megawatt for stage_result in stage_results])
            > self.maximum_power
            if self.maximum_power
            else False,
            target_pressure_status=target_pressure_status,
        )

    def evaluate_compressor_train_choking_train_inlet_stream_to_meet_target_discharge_pressure(
        self,
        speed: float,
        train_inlet_stream: Stream,
    ) -> CompressorTrainResultSingleTimeStep:
        def _evaluate_compressor_train_given_train_inlet_stream_and_speed(
            _inlet_pressure: float,
        ) -> CompressorTrainResultSingleTimeStep:
            return self.evaluate_compressor_train_given_train_inlet_stream_and_speed(
                train_inlet_stream=train_inlet_stream.create_stream_with_new_conditions(
                    conditions=ProcessConditions(
                        pressure_bara=_inlet_pressure,
                        temperature_kelvin=train_inlet_stream.temperature_kelvin,
                    )
                ),
                speed=speed,
            )

        choked_inlet_pressure = find_root(
            lower_bound=UnitConstants.STANDARD_PRESSURE_BARA
            + self.stages[0].pressure_drop_ahead_of_stage,  # Fixme: What is a sensible value here?
            upper_bound=self.target_suction_pressure,
            func=lambda x: _evaluate_compressor_train_given_train_inlet_stream_and_speed(
                _inlet_pressure=x
            ).discharge_pressure
            - self.target_discharge_pressure,
        )
        compressor_train_result = self.evaluate_compressor_train_given_train_inlet_stream_and_speed(
            speed=speed,
            train_inlet_stream=train_inlet_stream.create_stream_with_new_conditions(
                conditions=ProcessConditions(
                    pressure_bara=choked_inlet_pressure,
                    temperature_kelvin=train_inlet_stream.temperature_kelvin,
                )
            ),
        )
        if compressor_train_result.target_pressure_status == TargetPressureStatus.BELOW_TARGET_SUCTION_PRESSURE:
            new_inlet_stream = FluidStream(
                fluid_model=compressor_train_result.inlet_stream,
                pressure_bara=self.target_suction_pressure,
                temperature_kelvin=compressor_train_result.inlet_stream.temperature_kelvin,
            )
            compressor_train_result.inlet_stream = FluidStreamDTO.from_fluid_domain_object(
                fluid_stream=new_inlet_stream
            )
            compressor_train_result.target_pressure_status = self.check_target_pressures(
                calculated_suction_pressure=compressor_train_result.inlet_stream.pressure_bara,
                calculated_discharge_pressure=compressor_train_result.outlet_stream.pressure_bara,
            )

        return compressor_train_result

    def evaluate_compressor_train_recirculating_fraction_of_available_capacity_to_meet_target_discharge_pressure(
        self,
        speed: float,
        train_inlet_stream: Stream,
    ) -> CompressorTrainResultSingleTimeStep:
        # if full recirculation gives low enough pressure, iterate on asv_rate_fraction to reach the target
        def _evaluate_compressor_train_given_train_inlet_stream_speed_and_asv_rate_fraction(
            asv_rate_fraction: float,
        ) -> CompressorTrainResultSingleTimeStep:
            """Note that we use outside variables for clarity and to avoid class instances."""
            train_results_this_time_step = self.evaluate_compressor_train_given_train_inlet_stream_and_speed(
                train_inlet_stream=train_inlet_stream,
                speed=speed,
                asv_rate_fraction=asv_rate_fraction,
            )
            return train_results_this_time_step

        # first check if there is room for recirculation
        train_result_no_recirculation = self.evaluate_compressor_train_given_train_inlet_stream_and_speed(
            train_inlet_stream=train_inlet_stream,
            speed=speed,
        )
        if not train_result_no_recirculation.within_capacity:
            return train_result_no_recirculation
        # then check if full recirculation gives low enough discharge pressure
        train_result_max_recirculation = self.evaluate_compressor_train_given_train_inlet_stream_and_speed(
            train_inlet_stream=train_inlet_stream,
            speed=speed,
            asv_rate_fraction=1.0,
        )
        if not train_result_max_recirculation.discharge_pressure < self.target_discharge_pressure:
            msg = (
                f"Compressor train with inlet pressure {self.target_suction_pressure} and speed {speed} is not able"
                f"to reach the required discharge pressure {self.target_discharge_pressure} even with full recirculation. "
                f"Pressure control {self.pressure_control} not feasible."
            )
            logger.debug(msg)  # Todo: Consider fallback to upstream choke instead of failure?
            return train_result_max_recirculation

        result_asv_rate_margin = find_root(
            lower_bound=0.0,
            upper_bound=1.0,
            func=lambda x: _evaluate_compressor_train_given_train_inlet_stream_speed_and_asv_rate_fraction(
                asv_rate_fraction=x
            ).discharge_pressure
            - self.target_discharge_pressure,
        )
        return self.evaluate_compressor_train_given_train_inlet_stream_and_speed(
            train_inlet_stream=train_inlet_stream,
            speed=speed,
            asv_rate_fraction=result_asv_rate_margin,
        )

    def evaluate_compressor_train_recirculating_constant_pressure_ratio_to_meet_target_discharge_pressure(
        self,
        train_inlet_stream: Stream,
        speed: float,
    ) -> CompressorTrainResultSingleTimeStep:
        """
        Evaluate the compressor train using individual ASV pressure control to maintain a constant pressure ratio
        (discharge pressure / suction pressure) across all compressor stages.

        This method adjusts the anti-surge valves (ASVs) for each stage independently to achieve the required
        discharge pressure, ensuring the pressure ratio is equal for all stages.

        Args:
            speed (float): Shaft speed in rpm.
            train_inlet_stream (Stream): The inlet stream for the compressor train.

        Returns:
            CompressorTrainResultSingleTimeStep: The result of the evaluation for a single time step, including
            stage results, inlet/outlet streams, speed, and pressure status.
        """
        pressure_ratio_per_stage = self.calculate_pressure_ratios_per_stage(
            suction_pressure=self.target_suction_pressure,
            discharge_pressure=self.target_discharge_pressure,
        )
        stage_outlet_stream = train_inlet_stream
        stage_results = []
        for stage_number, stage in enumerate(self.stages):
            stage_inlet_stream = self._update_stream_between_stages(
                stage_number=stage_number,
                stage_outlet_stream=stage_outlet_stream,
            )
            outlet_pressure_for_stage = stage_inlet_stream.pressure_bara * pressure_ratio_per_stage
            stage_result = stage.evaluate_given_speed_and_target_discharge_pressure(
                target_discharge_pressure=outlet_pressure_for_stage,
                inlet_stream_stage=stage_inlet_stream,
                speed=speed,
            )
            stage_outlet_stream = stage_inlet_stream.create_stream_with_new_conditions(
                conditions=ProcessConditions(
                    pressure_bara=stage_result.outlet_stream.pressure_bara,
                    temperature_kelvin=stage_result.outlet_stream.temperature_kelvin,
                )
            )
            stage_results.append(stage_result)

        # check if target pressures are met
        target_pressure_status = self.check_target_pressures(
            calculated_suction_pressure=train_inlet_stream.pressure_bara,
            calculated_discharge_pressure=stage_results[-1].outlet_stream.pressure_bara,
        )
        return CompressorTrainResultSingleTimeStep(
            inlet_stream=FluidStreamDTO.from_fluid_process_object(fluid_stream=train_inlet_stream),
            outlet_stream=FluidStreamDTO.from_fluid_process_object(fluid_stream=stage_outlet_stream),
            speed=speed,
            stage_results=stage_results,
            target_pressure_status=target_pressure_status,
        )

    def evaluate_compressor_train_choking_train_outlet_stream_to_meet_target_discharge_pressure(
        self,
        train_result: CompressorTrainResultSingleTimeStep,
    ) -> CompressorTrainResultSingleTimeStep:
        """
        Adjusts the outlet stream of the compressor train to match the target discharge pressure by choking the outlet.

        If the calculated discharge pressure exceeds the target, this method updates the outlet stream's pressure
        to the target value and updates the pressure status accordingly.

        Args:
            train_result (CompressorTrainResultSingleTimeStep): The result of the compressor train evaluation before choking.

        Returns:
            CompressorTrainResultSingleTimeStep: The updated result with the outlet stream pressure set to the target discharge pressure if required.
        """
        if train_result.target_pressure_status == TargetPressureStatus.ABOVE_TARGET_DISCHARGE_PRESSURE:
            new_outlet_stream = FluidStream(
                fluid_model=train_result.outlet_stream,
                pressure_bara=self.target_discharge_pressure,
                temperature_kelvin=train_result.outlet_stream.temperature_kelvin,
            )
            train_result.outlet_stream = FluidStreamDTO.from_fluid_domain_object(fluid_stream=new_outlet_stream)
            train_result.target_pressure_status = self.check_target_pressures(
                calculated_suction_pressure=train_result.inlet_stream.pressure_bara,
                calculated_discharge_pressure=train_result.outlet_stream.pressure_bara,
            )
        return train_result

    def evaluate_compressor_train_using_pressure_control_at_given_speed(
        self,
        speed: float,
        train_inlet_stream: Stream,
    ) -> CompressorTrainResultSingleTimeStep:
        if self.pressure_control == FixedSpeedPressureControl.UPSTREAM_CHOKE:
            train_result = self.evaluate_compressor_train_choking_train_inlet_stream_to_meet_target_discharge_pressure(
                train_inlet_stream=train_inlet_stream,
                speed=speed,
            )
        elif self.pressure_control == FixedSpeedPressureControl.DOWNSTREAM_CHOKE:
            train_result = self.evaluate_compressor_train_given_train_inlet_stream_and_speed(
                speed=speed,
                train_inlet_stream=train_inlet_stream,
            )
            train_result = self.evaluate_compressor_train_choking_train_outlet_stream_to_meet_target_discharge_pressure(
                train_result=train_result,
            )
        elif self.pressure_control == FixedSpeedPressureControl.INDIVIDUAL_ASV_RATE:
            train_result = self.evaluate_compressor_train_recirculating_fraction_of_available_capacity_to_meet_target_discharge_pressure(
                train_inlet_stream=train_inlet_stream,
                speed=speed,
            )
        elif self.pressure_control == FixedSpeedPressureControl.INDIVIDUAL_ASV_PRESSURE:
            train_result = (
                self.evaluate_compressor_train_recirculating_constant_pressure_ratio_to_meet_target_discharge_pressure(
                    train_inlet_stream=train_inlet_stream,
                    speed=speed,
                )
            )
        # For INDIVIDUAL_ASV_PRESSURE and COMMON_ASV current solution is making a single speed equivalent train
        # Hence, there is no possibility for multiple streams entering/leaving the compressor train (when this option
        # is used for interstage pressure the sub-trains may be without multiple streams
        elif self.pressure_control == FixedSpeedPressureControl.COMMON_ASV:
            # Run as a single speed train with rate adjustment
            # Todo: not feasible if there is more than one stream going into compressor train?
            #       currently relying on only one stream entering the train controlled by
            #       asv and balanced pressure ratios
            (
                inlet_fluid_single_speed_train,
                updated_std_rates_std_m3_per_day_per_stream,
            ) = self._update_inlet_fluid_and_std_rates_for_last_subtrain(
                std_rates_std_m3_per_day_per_stream=self.target_stream_rates,
                inlet_pressure=self.target_suction_pressure,
            )

            if len(updated_std_rates_std_m3_per_day_per_stream) > 1:
                raise NotImplementedError(
                    "Making a single speed train using asv and balanced pressure ratios not implemented "
                    "when there are multiple streams entering the subtrain in question"
                )
            else:
                inlet_rate_single_speed_train = updated_std_rates_std_m3_per_day_per_stream[0]

            single_speed_compressor_stages = [
                CompressorTrainStage(
                    compressor_chart=get_single_speed_equivalent(compressor_chart=stage.compressor_chart, speed=speed),
                    inlet_temperature_kelvin=stage.inlet_temperature_kelvin,
                    remove_liquid_after_cooling=stage.remove_liquid_after_cooling,
                    pressure_drop_ahead_of_stage=stage.pressure_drop_ahead_of_stage,
                )
                for stage in self.stages
            ]

            single_speed_train = SingleSpeedCompressorTrainCommonShaft(
                data_transfer_object=SingleSpeedCompressorTrain(
                    fluid_model=inlet_fluid_single_speed_train.fluid_model,
                    stages=[
                        CompressorStage(
                            compressor_chart=SingleSpeedChartDTO(
                                speed_rpm=stage.compressor_chart.speed,
                                rate_actual_m3_hour=list(stage.compressor_chart.rate_values),
                                polytropic_head_joule_per_kg=list(stage.compressor_chart.head_values),
                                efficiency_fraction=list(stage.compressor_chart.efficiency_values),
                            ),
                            inlet_temperature_kelvin=stage.inlet_temperature_kelvin,
                            remove_liquid_after_cooling=stage.remove_liquid_after_cooling,
                            pressure_drop_before_stage=stage.pressure_drop_ahead_of_stage,
                            control_margin=0,
                        )
                        for stage in single_speed_compressor_stages
                    ],
                    pressure_control=self.pressure_control,
                    maximum_discharge_pressure=None,
                    energy_usage_adjustment_constant=0.0,  # Fixme: Need to transfer this from the input DTO.
                    energy_usage_adjustment_factor=1.0,  # Fixme: Need to transfer this from the input DTO.
                ),
            )
            single_speed_train._set_evaluate_constraints(
                rate=inlet_rate_single_speed_train,
                suction_pressure=self.target_suction_pressure,
                discharge_pressure=self.target_discharge_pressure,
            )
            single_speed_train_results = single_speed_train._evaluate()
            train_result = single_speed_train_results
            train_result.speed = speed
        else:
            raise IllegalStateException(
                f"Pressure control {self.pressure_control} not supported, should be one of"
                f"{list(FixedSpeedPressureControl)}. Should not end up here, please contact support."
            )

        return train_result

    def _update_inlet_fluid_and_std_rates_for_last_subtrain(
        self,
        std_rates_std_m3_per_day_per_stream: list[float],
        inlet_pressure: float,
    ) -> tuple[FluidStream, list[float]]:
        """ """
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
            fluid_to_recirculate = self.get_stream_to_recirculate_in_stage_when_inlet_rate_is_zero(stage_number=0)
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
        train_inlet_stream: Stream,
        pressure_control_first_part: FixedSpeedPressureControl,
        pressure_control_last_part: FixedSpeedPressureControl,
    ) -> CompressorTrainResultSingleTimeStep:
        """Compressor train has two pressure targets, one interstage target at which typically a stream is going out of or
        into the train, and one pressure target for the final discharge pressure after the last stage.
        Typical example when part of the gas is taken out for export at one stage and the rest continues to the next
        stage(s) for injection at higher pressure.

        The model behaviour is based on an assumption of how the train is regulated to meet the target pressures in the
        following way:
         - speed is set such that the pressure requirements may be met at both pressure intervals; inlet to intermediate
           and intermediate to discharge
         - the part of the train which will get a too high pressure increase with this speed, will now use one of three
           strategies to meet the target outlet of this subtrain; upstream choking, downstream choking, using asv to
           increase head (for this speed) until target outlet pressure is met.
        """
        # Split train into two and calculate minimum speed to reach required pressures
        if not self.target_intermediate_pressure:
            raise ValueError(
                "The compressor train does not have an intermediate pressure target. "
                "Please use the evaluate_compressor_train_given_train_inlet_stream_and_target_discharge_pressure method."
            )
        else:
            compressor_train_first_part, compressor_train_last_part = split_train_on_stage_number(
                compressor_train=self,
                stage_number=stage_number_for_intermediate_pressure_target,
                pressure_control_first_part=pressure_control_first_part,
                pressure_control_last_part=pressure_control_last_part,
            )
            std_rates_first_part, std_rates_last_part = split_rates_on_stage_number(
                compressor_train=self,
                rates_per_stream=self.target_stream_rates,
                stage_number=stage_number_for_intermediate_pressure_target,
            )
            compressor_train_first_part._set_evaluate_constraints(
                rate=std_rates_first_part,
                suction_pressure=self.target_suction_pressure,
                discharge_pressure=self.target_intermediate_pressure,
            )
            compressor_train_last_part._set_evaluate_constraints(
                rate=std_rates_last_part,
                suction_pressure=self.target_intermediate_pressure,
                discharge_pressure=self.target_discharge_pressure,
            )

            compressor_train_results_first_part_with_optimal_speed_result = compressor_train_first_part.evaluate_compressor_train_given_train_inlet_stream_and_target_discharge_pressure(
                train_inlet_stream=train_inlet_stream,
                lower_bound_for_speed=self.minimum_speed,  # Only search for a solution within the bounds of the
                upper_bound_for_speed=self.maximum_speed,  # original, complete compressor train
            )

            if self.data_transfer_object.calculate_max_rate:
                max_standard_rate_per_stream = [
                    compressor_train_first_part._get_max_rate_for_single_stream_single_timestep(
                        suction_pressure=self.target_suction_pressure,
                        target_discharge_pressure=self.target_intermediate_pressure,
                        rate_per_stream=std_rates_first_part,
                        stream_to_maximize=stream_index,
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
            compressor_train_last_part_inlet_stream = Stream.from_standard_rate(
                thermo_system=NeqSimThermoSystem(
                    composition=compressor_train_last_part.streams[0].fluid.fluid_model.composition,
                    eos_model=compressor_train_last_part.streams[0].fluid.fluid_model.eos_model,
                    conditions=ProcessConditions(
                        temperature_kelvin=compressor_train_last_part.stages[0].inlet_temperature_kelvin,
                        pressure_bara=compressor_train_last_part.target_suction_pressure,
                    ),
                ),
                standard_rate=std_rates_last_part[0],
            )

            compressor_train_results_last_part_with_optimal_speed_result = compressor_train_last_part.evaluate_compressor_train_given_train_inlet_stream_and_target_discharge_pressure(
                train_inlet_stream=compressor_train_last_part_inlet_stream,
                lower_bound_for_speed=self.minimum_speed,
                upper_bound_for_speed=self.maximum_speed,
            )

            if self.data_transfer_object.calculate_max_rate:
                for stream_index, _ in enumerate(compressor_train_last_part.streams):
                    if stream_index > 0:
                        max_standard_rate_per_stream.append(
                            compressor_train_first_part._get_max_rate_for_single_stream_single_timestep(
                                suction_pressure=self.target_intermediate_pressure,
                                target_discharge_pressure=self.target_discharge_pressure,
                                rate_per_stream=std_rates_last_part,
                                stream_to_maximize=stream_index,
                            )
                        )
            else:
                max_standard_rate_per_stream = max_standard_rate_per_stream + [float("nan")] * len(
                    std_rates_last_part[1:]
                )
            """
            Determine which of the first and last part will govern the speed to use
            Then run the last part as a single speed train with the speed chosen
            Fixme: Need to deliver the result in a proper format below.
            """
            if (
                compressor_train_results_first_part_with_optimal_speed_result.speed
                > compressor_train_results_last_part_with_optimal_speed_result.speed
            ):
                speed = compressor_train_results_first_part_with_optimal_speed_result.speed
                compressor_train_results_last_part_with_pressure_control = (
                    compressor_train_last_part.evaluate_compressor_train_using_pressure_control_at_given_speed(
                        train_inlet_stream=compressor_train_last_part_inlet_stream,
                        speed=speed,
                    )
                )
                compressor_train_results_to_return_first_part = (
                    compressor_train_results_first_part_with_optimal_speed_result
                )
                compressor_train_results_to_return_last_part = compressor_train_results_last_part_with_pressure_control

            else:
                speed = compressor_train_results_last_part_with_optimal_speed_result.speed
                compressor_train_results_first_part_with_pressure_control = (
                    compressor_train_first_part.evaluate_compressor_train_using_pressure_control_at_given_speed(
                        train_inlet_stream=train_inlet_stream,
                        speed=speed,
                    )
                )
                compressor_train_results_to_return_first_part = (
                    compressor_train_results_first_part_with_pressure_control
                )
                compressor_train_results_to_return_last_part = (
                    compressor_train_results_last_part_with_optimal_speed_result
                )

            compressor_train_results_to_return_stage_results = list(
                compressor_train_results_to_return_first_part.stage_results
                + compressor_train_results_to_return_last_part.stage_results
            )

            for stage_number in range(len(self.stages)):
                self.set_stream_to_recirculate_in_stage_when_inlet_rate_is_zero(
                    stage_number=stage_number,
                    stream=compressor_train_first_part.get_stream_to_recirculate_in_stage_when_inlet_rate_is_zero(
                        stage_number=stage_number
                    )
                    if stage_number < stage_number_for_intermediate_pressure_target
                    else compressor_train_last_part.get_stream_to_recirculate_in_stage_when_inlet_rate_is_zero(
                        stage_number=stage_number - stage_number_for_intermediate_pressure_target
                    ),
                )

            # check if target pressures are met
            target_pressure_status = self.check_target_pressures(
                calculated_suction_pressure=compressor_train_results_to_return_first_part.inlet_stream.pressure_bara,
                calculated_discharge_pressure=compressor_train_results_to_return_last_part.outlet_stream.pressure_bara,
                calculated_intermediate_pressure=compressor_train_results_to_return_first_part.outlet_stream.pressure_bara,
            )

            return CompressorTrainResultSingleTimeStep(
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
                target_pressure_status=target_pressure_status,
            )

    def set_stream_to_recirculate_in_stage_when_inlet_rate_is_zero(self, stage_number: int, stream: Stream) -> None:
        """
        Keep track of what fluid passes through each compressor stage in the compressor train at a given calculation
        step. This is done in case of the possibility of having a zero inlet rate at the next calculation step when
        adding/subtracting ingoing/outgoing streams. The stream is stored with rate 0.0.

        Args:
            stage_number: The stage number (zero index)
            stream: The fluid stream passing through compressor stage number <stage_number>
        """
        self.stream_to_recirculate_in_stage_when_inlet_rate_is_zero[stage_number] = (
            Stream(
                thermo_system=stream.thermo_system,
                mass_rate=0.0,
            )
            if stream is not None
            else None
        )

    def get_stream_to_recirculate_in_stage_when_inlet_rate_is_zero(self, stage_number: int) -> Stream:
        """Retrieve the fluid that passed through a given compressor stage in the compressor train at the previous
        calculation step. The rate will be EPSILON, and the compressor stage needs to recirculate that rate up to
        its minimum rate.

        Arge:
            stage_number: The stage number (zero index)

        """
        return self.stream_to_recirculate_in_stage_when_inlet_rate_is_zero[stage_number]


def split_rates_on_stage_number(
    compressor_train: VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures,
    rates_per_stream: list[float],
    stage_number: int,
) -> tuple[list[float], list[float]]:
    """ """
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
    """Split train into two and calculate minimum speed to reach required pressures.

    :param compressor_train: Variable speed compressor train
    :param stage_number:
    :return:
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
            compressor_train_first_part.set_stream_to_recirculate_in_stage_when_inlet_rate_is_zero(
                stage_number=stage_no,
                stream=compressor_train.get_stream_to_recirculate_in_stage_when_inlet_rate_is_zero(stage_no),
            )
        else:
            compressor_train_last_part.set_stream_to_recirculate_in_stage_when_inlet_rate_is_zero(
                stage_number=stage_no - stage_number,
                stream=compressor_train.get_stream_to_recirculate_in_stage_when_inlet_rate_is_zero(stage_no),
            )

    return compressor_train_first_part, compressor_train_last_part
