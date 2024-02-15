from copy import deepcopy
from functools import partial
from typing import Dict, List, Optional, Tuple, cast

import numpy as np
from numpy.typing import NDArray

from libecalc import dto
from libecalc.common.errors.exceptions import EcalcError, IllegalStateException
from libecalc.common.logger import logger
from libecalc.common.units import Unit, UnitConstants
from libecalc.core.models import ModelInputFailureStatus, validate_model_input
from libecalc.core.models.compressor.results import CompressorTrainResultSingleTimeStep
from libecalc.core.models.compressor.train.base import CompressorTrainModel
from libecalc.core.models.compressor.train.fluid import FluidStream
from libecalc.core.models.compressor.train.single_speed_compressor_train_common_shaft import (
    SingleSpeedCompressorTrainCommonShaft,
)
from libecalc.core.models.compressor.train.stage import CompressorTrainStage
from libecalc.core.models.compressor.train.types import (
    FluidStreamObjectForMultipleStreams,
)
from libecalc.core.models.compressor.train.utils.common import (
    POWER_CALCULATION_TOLERANCE,
    PRESSURE_CALCULATION_TOLERANCE,
    RATE_CALCULATION_TOLERANCE,
)
from libecalc.core.models.compressor.train.utils.numeric_methods import (
    find_root,
    maximize_x_given_boolean_condition_function,
)
from libecalc.core.models.compressor.train.utils.variable_speed_compressor_train_common_shaft import (
    get_single_speed_equivalent,
)
from libecalc.core.models.results import CompressorTrainResult
from libecalc.core.models.results.compressor import (
    CompressorTrainCommonShaftFailureStatus,
)
from libecalc.domain.stream_conditions import StreamConditions
from libecalc.dto.types import FixedSpeedPressureControl

EPSILON = 1e-5


class VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures(
    CompressorTrainModel[dto.VariableSpeedCompressorTrainMultipleStreamsAndPressures]
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
        data_transfer_object: dto.VariableSpeedCompressorTrainMultipleStreamsAndPressures,
        streams: List[FluidStreamObjectForMultipleStreams],
    ):
        logger.debug(
            f"Creating {type(self).__name__} with\n"
            f"n_stages: {len(data_transfer_object.stages)} and n_streams: {len(streams)}"
        )
        super().__init__(data_transfer_object=data_transfer_object)
        self.streams = streams
        self.number_of_compressor_streams = len(self.streams)

        self.inlet_stream_connected_to_stage: Dict[int, List[int]] = {key: [] for key in range(len(self.stages))}
        self.outlet_stream_connected_to_stage: Dict[int, List[int]] = {key: [] for key in range(len(self.stages))}
        for i, stream in enumerate(self.streams):
            if stream.is_inlet_stream:
                self.inlet_stream_connected_to_stage[stream.connected_to_stage_no].append(i)
            else:
                self.outlet_stream_connected_to_stage[stream.connected_to_stage_no].append(i)

        # in rare cases we can end up with trying to mix two streams with zero mass rate, and need the fluid from the
        # previous time step to recirculate. This will take care of that.
        self.fluid_to_recirculate_in_stage_when_inlet_rate_is_zero = [None] * len(self.stages)

    def evaluate_streams(
        self,
        inlet_streams: List[StreamConditions],
        outlet_stream: StreamConditions,
    ) -> CompressorTrainResult:
        """
        Evaluate model based on inlet streams and the expected outlet stream.
        Args:
            inlet_streams:
            outlet_stream:

        Returns:

        """

        if len(inlet_streams) != len(self.streams):
            named_streams = [inlet_stream.name for inlet_stream in inlet_streams if inlet_stream.name]
            raise EcalcError(
                title="Validation error",
                message=f"Mismatch in streams. "
                f'Required streams are {", ".join(stream.name for stream in self.streams)}. '
                f'Received named streams are {", ".join(named_streams) if len(named_streams) > 0 else "none"}'
                f" + {len(inlet_streams) - len(named_streams)} unnamed stream(s).",
            )

        # Order streams either based on name or use index
        stream_index_counter = 0
        ordered_streams: List[StreamConditions] = []
        for stream_definition in self.streams:
            try:
                inlet_stream = next(
                    inlet_stream for inlet_stream in inlet_streams if inlet_stream.name == stream_definition.name
                )
                ordered_streams.append(inlet_stream)
            except StopIteration:
                ordered_streams.append(inlet_streams[stream_index_counter])
                stream_index_counter += 1

        # Currently ignoring pressures in intermediate streams

        return self.evaluate_rate_ps_pd(
            rate=np.asarray(
                [[inlet_stream.rate.value] for inlet_stream in ordered_streams]
            ),  # TODO: This can also contain rates defined as outlet streams
            suction_pressure=np.asarray([inlet_streams[0].pressure.value]),
            discharge_pressure=np.asarray([outlet_stream.pressure.value]),
        )

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

    def _evaluate_rate_ps_pd(
        self, rate: NDArray[np.float64], suction_pressure: NDArray[np.float64], discharge_pressure: NDArray[np.float64]
    ) -> List[CompressorTrainResultSingleTimeStep]:
        # Iterate over input points, calculate one by one
        train_results = []
        for time_step, (
            suction_pressure_this_time_step,
            discharge_pressure_this_time_step,
        ) in enumerate(zip(suction_pressure, discharge_pressure)):
            std_rates_std_m3_per_day_per_stream_this_time_step = (
                self.check_that_ingoing_streams_are_larger_than_or_equal_to_outgoing_streams(rate[:, time_step])
            )
            inlet_rates_this_time_step = [
                std_rates_std_m3_per_day_per_stream_this_time_step[i]
                for (i, stream) in enumerate(self.streams)
                if stream.is_inlet_stream
            ]
            # Enough with one positive ingoing stream. Compressors with possible zero rates will recirculate
            positive_ingoing_streams = list(filter(lambda x: x > 0, list(inlet_rates_this_time_step)))
            if not any(positive_ingoing_streams):
                train_results.append(
                    CompressorTrainResultSingleTimeStep.create_empty(number_of_stages=len(self.stages))
                )
            else:
                compressor_train_result = self.calculate_shaft_speed_given_rate_ps_pd(
                    std_rates_std_m3_per_day_per_stream=std_rates_std_m3_per_day_per_stream_this_time_step,
                    suction_pressure=suction_pressure_this_time_step,
                    target_discharge_pressure=discharge_pressure_this_time_step,
                )
                train_results.append(compressor_train_result)

        return train_results

    def check_that_ingoing_streams_are_larger_than_or_equal_to_outgoing_streams(
        self,
        std_rates_std_m3_per_day_per_stream: NDArray[np.float64],
    ) -> NDArray[np.float64]:
        """Check that for all stages in the compressor train, the sum of the ingoing streams in the compressor train
        up to that stage is at least as much as the outgoing streams up to that stage. A compressor train can not make
        fluids (that would be nice...).

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
                return np.multiply(std_rates_std_m3_per_day_per_stream, 0)

        return std_rates_std_m3_per_day_per_stream

    def convert_to_rates_for_each_compressor_train_stages(self, rates_per_stream: NDArray[np.float64]) -> List[float]:
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

    def calculate_shaft_speed_given_rate_ps_pd(
        self,
        std_rates_std_m3_per_day_per_stream: NDArray[np.float64],
        suction_pressure: float,
        target_discharge_pressure: float,
        lower_bound_for_speed: Optional[float] = None,
        upper_bound_for_speed: Optional[float] = None,
    ) -> CompressorTrainResultSingleTimeStep:
        """Run compressor train forward model with inlet conditions and speed, and iterate on speed until discharge
        pressure meets requested discharge pressure.

        :param std_rates_std_m3_per_day_per_stream: The inlet rates for each stream in the compressor train,
        :param suction_pressure: The inlet pressure of the compressor train,
        :param target_discharge_pressure: The outlet pressure of the compressor train,
        :param lower_bound_for_speed: Optional lower boundary for rotational speed for the compressor shaft, if not
                                         defined the lowest speed in the compressor chart curves is used.
        :param upper_bound_for_speed: Optional upper boundary for rotational speed for the compressor shaft, if not
                                         defined the highest speed in the compressor chart curves is used.

        :returns: The result of the compressor train calculations
        """
        minimum_speed = lower_bound_for_speed if lower_bound_for_speed else self.minimum_speed
        maximum_speed = upper_bound_for_speed if upper_bound_for_speed else self.maximum_speed

        def _calculate_train_result_given_rate_ps_speed(
            _speed: float,
        ) -> CompressorTrainResultSingleTimeStep:
            return self.calculate_compressor_train_given_rate_ps_speed(
                inlet_pressure_bara=suction_pressure,
                std_rates_std_m3_per_day_per_stream=std_rates_std_m3_per_day_per_stream,
                speed=_speed,
            )

        train_result_for_minimum_speed = _calculate_train_result_given_rate_ps_speed(_speed=minimum_speed)
        train_result_for_maximum_speed = _calculate_train_result_given_rate_ps_speed(_speed=maximum_speed)

        if not train_result_for_maximum_speed.is_valid:
            # will not find valid result - the rate is above maximum rate, return invalid results at maximum speed
            return train_result_for_maximum_speed
        if not train_result_for_minimum_speed.is_valid:
            # rate is above maximum rate for minimum speed. Find the lowest minimum speed which gives a valid result
            minimum_speed = -maximize_x_given_boolean_condition_function(
                x_min=-self.maximum_speed,
                x_max=-self.minimum_speed,
                bool_func=lambda x: _calculate_train_result_given_rate_ps_speed(_speed=-x).is_valid,
            )
            train_result_for_minimum_speed = _calculate_train_result_given_rate_ps_speed(_speed=minimum_speed)

        # Solution 1, iterate on speed until target discharge pressure is found
        if (
            train_result_for_minimum_speed.discharge_pressure
            <= target_discharge_pressure
            <= train_result_for_maximum_speed.discharge_pressure
        ):
            speed = find_root(
                lower_bound=minimum_speed,
                upper_bound=maximum_speed,
                func=lambda x: _calculate_train_result_given_rate_ps_speed(_speed=x).discharge_pressure
                - target_discharge_pressure,
            )

            return _calculate_train_result_given_rate_ps_speed(_speed=speed)

        # Solution 2, try pressure control mechanism or target pressure is too low:
        elif target_discharge_pressure < train_result_for_minimum_speed.discharge_pressure:
            if self.pressure_control:
                return self.calculate_compressor_train_given_rate_ps_pd_speed(
                    speed=minimum_speed,
                    std_rates_std_m3_per_day_per_stream=std_rates_std_m3_per_day_per_stream,
                    inlet_pressure=suction_pressure,
                    outlet_pressure=target_discharge_pressure,
                )
            else:
                train_result_for_minimum_speed.failure_status = (
                    CompressorTrainCommonShaftFailureStatus.TARGET_DISCHARGE_PRESSURE_TOO_LOW
                )
                return train_result_for_minimum_speed
        # Solution 3, target discharge pressure is too high
        else:
            train_result_for_maximum_speed.failure_status = (
                CompressorTrainCommonShaftFailureStatus.TARGET_DISCHARGE_PRESSURE_TOO_HIGH
            )
            return train_result_for_maximum_speed

    def get_max_standard_rate(
        self,
        suction_pressures: Optional[NDArray[np.float64]] = None,
        discharge_pressures: Optional[NDArray[np.float64]] = None,
    ) -> NDArray[np.float64]:
        """Calculate the max standard rate [Sm3/day] that the compressor train can operate at."""
        raise NotImplementedError("This method is not implemented for multiple streams and pressures")

    def get_max_standard_rate_per_stream(
        self,
        suction_pressures: NDArray[np.float64],
        discharge_pressures: NDArray[np.float64],
        rates_per_stream: NDArray[np.float64],
    ) -> NDArray[np.float64]:
        """Calculate the max standard rate [Sm3/day] the compressor train can operate at for each stream.

        When the max standard rate for one stream is calculated, all other streams are kept constant at the values
        given in rates_per_stream. This means that changing the rates for more than one stream to the max available
        rate will not be meaningful.
        """
        max_std_rate_per_stream = []
        for stream_index, _ in enumerate(self.streams):
            max_std_rates = []
            for (
                time_step,
                (suction_pressure, discharge_pressure),
            ) in enumerate(zip(suction_pressures, discharge_pressures)):
                try:
                    max_std_rate = self._get_max_rate_for_single_stream_single_timestep(
                        suction_pressure=suction_pressure,
                        target_discharge_pressure=discharge_pressure,
                        rate_per_stream=np.array([stream_rate[time_step] for stream_rate in rates_per_stream]),
                        stream_to_maximize=stream_index,
                    )
                except EcalcError as e:
                    logger.exception(e)
                    max_std_rate = np.nan

                max_std_rates.append(max_std_rate)

            max_std_rate_per_stream.append(np.array(max_std_rates))

        return np.array(max_std_rate_per_stream)

    def _get_max_rate_for_single_stream_single_timestep(
        self,
        suction_pressure: float,
        target_discharge_pressure: float,
        rate_per_stream: NDArray[np.float64],
        stream_to_maximize: int,
        allow_asv: bool = False,
    ) -> float:
        """NB: Constraining to calculating maximum_rate for ingoing streams for now - the need is to figure out how much rate
        can be added.

        """
        stream_to_maximize_connected_to_stage_no = self.streams[stream_to_maximize].connected_to_stage_no

        # if it is not an ingoing stream --> currently no calculations done
        # Fixme: what should be returned? 0.0, NaN or something else?
        if not self.streams[stream_to_maximize].is_inlet_stream:
            return np.nan

        std_rates_std_m3_per_day_per_stream = rate_per_stream.copy()

        def _calculate_train_result(std_rate_for_stream: float, speed: float) -> CompressorTrainResultSingleTimeStep:
            """Partial function of self.calculate_compressor_train_given_rate_ps_speed
            where we only pass std_rate_per_stream and speed.
            """
            std_rates_std_m3_per_day_per_stream[stream_to_maximize] = std_rate_for_stream
            return self.calculate_compressor_train_given_rate_ps_speed(
                inlet_pressure_bara=suction_pressure,
                std_rates_std_m3_per_day_per_stream=std_rates_std_m3_per_day_per_stream,
                speed=speed,
            )

        def _calculate_train_first_part_result(speed: float) -> CompressorTrainResultSingleTimeStep:
            """ """
            return train_first_part.calculate_compressor_train_given_rate_ps_speed(
                inlet_pressure_bara=suction_pressure,
                std_rates_std_m3_per_day_per_stream=std_rates_std_m3_per_day_per_stream_first_part,
                speed=speed,
            )

        def _calculate_train_result_given_speed_at_stone_wall(
            speed: float,
        ) -> Tuple[float, CompressorTrainResultSingleTimeStep]:
            """Partial function of self.calculate_compressor_train_given_rate_ps_speed.
            Same as above, but mass rate is pinned to the "stone wall" as a function of speed.
            """
            if stream_to_maximize_connected_to_stage_no > 0:
                train_first_part_result = _calculate_train_first_part_result(speed)
                stream_density = (
                    self.streams[stream_to_maximize]
                    .fluid.get_fluid_stream(
                        pressure_bara=train_first_part_result.discharge_pressure
                        - self.stages[stream_to_maximize_connected_to_stage_no].pressure_drop_ahead_of_stage,
                        temperature_kelvin=self.stages[
                            stream_to_maximize_connected_to_stage_no
                        ].inlet_temperature_kelvin,
                    )
                    .density
                )
                train_first_part_actual_rate_m3_per_hr = train_first_part_result.stage_results[
                    -1
                ].outlet_actual_rate_m3_per_hour
            else:
                stream_density = (
                    self.streams[0]
                    .fluid.get_fluid_stream(
                        pressure_bara=suction_pressure,
                        temperature_kelvin=self.stages[0].inlet_temperature_kelvin,
                    )
                    .density
                )
                train_first_part_actual_rate_m3_per_hr = 0

            x_min_mass_rate_kg_per_hr = (
                max(
                    0,
                    self.stages[
                        stream_to_maximize_connected_to_stage_no
                    ].compressor_chart.minimum_rate_as_function_of_speed(speed)
                    - train_first_part_actual_rate_m3_per_hr,
                )
                * stream_density
            )
            x_max_mass_rate_kg_per_hr = (
                max(
                    0,
                    self.stages[
                        stream_to_maximize_connected_to_stage_no
                    ].compressor_chart.maximum_rate_as_function_of_speed(speed)
                    - train_first_part_actual_rate_m3_per_hr,
                )
                * stream_density
            )
            _max_valid_std_rate_for_stream_at_given_speed = maximize_x_given_boolean_condition_function(
                x_min=self.streams[stream_to_maximize].fluid.mass_rate_to_standard_rate(
                    mass_rate_kg_per_hour=x_min_mass_rate_kg_per_hr
                ),
                x_max=self.streams[stream_to_maximize].fluid.mass_rate_to_standard_rate(
                    mass_rate_kg_per_hour=x_max_mass_rate_kg_per_hr
                ),
                bool_func=lambda x: _calculate_train_result(std_rate_for_stream=x, speed=speed).is_valid,
            )

            std_rates_std_m3_per_day_per_stream[stream_to_maximize] = _max_valid_std_rate_for_stream_at_given_speed

            return (
                _max_valid_std_rate_for_stream_at_given_speed,
                self.calculate_compressor_train_given_rate_ps_speed(
                    inlet_pressure_bara=suction_pressure,
                    std_rates_std_m3_per_day_per_stream=std_rates_std_m3_per_day_per_stream,
                    speed=speed,
                ),
            )

        # Same as the partial functions above, but simpler syntax using partial()
        _calculate_train_result_at_max_speed_given_std_rate_for_stream = partial(
            _calculate_train_result, speed=self.maximum_speed
        )
        _calculate_train_result_at_min_speed_given_std_rate_for_stream = partial(
            _calculate_train_result, speed=self.minimum_speed
        )

        # Use compressor that the ingoing stream is connected to as bounds - need to take into account all other
        # streams up to that point (in- and outgoing)
        # Make, and calculate subtrain

        if stream_to_maximize_connected_to_stage_no > 0:
            train_first_part, _ = split_train_on_stage_number(
                compressor_train=self,
                stage_number=stream_to_maximize_connected_to_stage_no,
            )
            std_rates_std_m3_per_day_per_stream_first_part, _ = split_rates_on_stage_number(
                compressor_train=self,
                rates_per_stream=std_rates_std_m3_per_day_per_stream,
                stage_number=stream_to_maximize_connected_to_stage_no,
            )
            train_first_part_result_at_min_speed = _calculate_train_first_part_result(
                speed=self.minimum_speed,
            )
            train_first_part_outlet_actual_rate_m3_per_hour_at_min_speed = (
                train_first_part_result_at_min_speed.stage_results[-1].outlet_actual_rate_m3_per_hour
            )
            # Fixme: with or without pressure drop ahead of stage?
            stream_density_at_min_speed = (
                self.streams[stream_to_maximize]
                .fluid.get_fluid_stream(
                    pressure_bara=train_first_part_result_at_min_speed.discharge_pressure
                    - self.stages[stream_to_maximize_connected_to_stage_no].pressure_drop_ahead_of_stage,
                    temperature_kelvin=self.stages[stream_to_maximize_connected_to_stage_no].inlet_temperature_kelvin,
                )
                .density
            )
            train_first_part_result_at_max_speed = _calculate_train_first_part_result(
                speed=self.maximum_speed,
            )
            train_first_part_outlet_actual_rate_m3_per_hour_at_max_speed = (
                train_first_part_result_at_max_speed.stage_results[-1].outlet_actual_rate_m3_per_hour
            )
            # Fixme: with or without pressure drop ahead of stage?
            stream_density_at_max_speed = (
                self.streams[stream_to_maximize]
                .fluid.get_fluid_stream(
                    pressure_bara=train_first_part_result_at_max_speed.discharge_pressure
                    - self.stages[stream_to_maximize_connected_to_stage_no].pressure_drop_ahead_of_stage,
                    temperature_kelvin=self.stages[stream_to_maximize_connected_to_stage_no].inlet_temperature_kelvin,
                )
                .density
            )
        else:
            # There is no "train-first-part"
            train_first_part_outlet_actual_rate_m3_per_hour_at_min_speed = 0
            train_first_part_outlet_actual_rate_m3_per_hour_at_max_speed = 0
            # can we have multiple streams in at a single inlet?
            stream_density_at_min_speed = stream_density_at_max_speed = (
                self.streams[0]
                .fluid.get_fluid_stream(
                    pressure_bara=suction_pressure,
                    temperature_kelvin=self.stages[0].inlet_temperature_kelvin,
                )
                .density
            )

        # subtract the actual rate coming from previous compressor from the minimum rate for compressor at current stage
        min_actual_rate_m3_per_hr_at_max_speed = max(
            self.stages[stream_to_maximize_connected_to_stage_no].compressor_chart.maximum_speed_curve.minimum_rate
            - train_first_part_outlet_actual_rate_m3_per_hour_at_max_speed,
            0,
        )
        max_actual_rate_m3_per_hr_at_max_speed = max(
            self.stages[stream_to_maximize_connected_to_stage_no].compressor_chart.maximum_speed_curve.maximum_rate
            - train_first_part_outlet_actual_rate_m3_per_hour_at_max_speed,
            0,
        )
        max_actual_rate_m3_per_hr_at_min_speed = max(
            self.stages[stream_to_maximize_connected_to_stage_no].compressor_chart.maximum_rate_as_function_of_speed(
                self.stages[stream_to_maximize_connected_to_stage_no].compressor_chart.minimum_speed
            )
            - train_first_part_outlet_actual_rate_m3_per_hour_at_min_speed,
            0,
        )

        # going from actual rate to std rate via mass rate m3/hr -> kg/hr -> m3/day (can we go directly?)
        min_mass_rate_kg_per_hr_at_max_speed = min_actual_rate_m3_per_hr_at_max_speed * stream_density_at_max_speed
        max_mass_rate_kg_per_hr_at_max_speed = max_actual_rate_m3_per_hr_at_max_speed * stream_density_at_max_speed
        max_mass_rate_kg_per_hr_at_min_speed = max_actual_rate_m3_per_hr_at_min_speed * stream_density_at_min_speed

        min_std_rate_for_stream_m3_per_day_at_max_speed = self.streams[
            stream_to_maximize
        ].fluid.mass_rate_to_standard_rate(mass_rate_kg_per_hour=min_mass_rate_kg_per_hr_at_max_speed) * (
            1 + RATE_CALCULATION_TOLERANCE
        )
        max_std_rate_for_stream_m3_per_day_at_max_speed = self.streams[
            stream_to_maximize
        ].fluid.mass_rate_to_standard_rate(mass_rate_kg_per_hour=max_mass_rate_kg_per_hr_at_max_speed) * (
            1 - RATE_CALCULATION_TOLERANCE
        )
        max_std_rate_for_stream_m3_per_day_at_min_speed = self.streams[
            stream_to_maximize
        ].fluid.mass_rate_to_standard_rate(mass_rate_kg_per_hour=max_mass_rate_kg_per_hr_at_min_speed) * (
            1 - RATE_CALCULATION_TOLERANCE
        )

        result_min_std_rate_for_stream_at_max_speed = _calculate_train_result_at_max_speed_given_std_rate_for_stream(
            std_rate_for_stream=min_std_rate_for_stream_m3_per_day_at_max_speed
        )
        result_max_std_rate_for_stream_at_max_speed = _calculate_train_result_at_max_speed_given_std_rate_for_stream(
            std_rate_for_stream=max_std_rate_for_stream_m3_per_day_at_max_speed
        )
        result_max_std_rate_for_stream_at_min_speed = _calculate_train_result_at_min_speed_given_std_rate_for_stream(
            std_rate_for_stream=max_std_rate_for_stream_m3_per_day_at_min_speed
        )

        # Ensure that the minimum std rate for stream at max speed is valid for the whole train.
        # Fixme: Logger debug messages
        if not result_min_std_rate_for_stream_at_max_speed.is_valid:
            if allow_asv:
                min_std_rate_m3_per_day_at_max_speed = EPSILON
                result_min_std_rate_at_max_speed = _calculate_train_result_at_max_speed_given_std_rate_for_stream(
                    mass_rate=min_std_rate_m3_per_day_at_max_speed
                )
                if not result_min_std_rate_at_max_speed.is_valid:
                    logger.debug(
                        "There are no valid std rate for stream {stream_to_maximize} for "
                        "VariableSpeedCompressorTrainMultipleStreamsAndPressures. "
                        "Infeasible solution. Returning max rate 0.0 (None)."
                    )
                    return 0.0
                max_std_rate_m3_per_day_at_max_speed = maximize_x_given_boolean_condition_function(
                    x_min=EPSILON,
                    x_max=min_std_rate_for_stream_m3_per_day_at_max_speed,
                    bool_func=lambda x: _calculate_train_result_at_max_speed_given_std_rate_for_stream(
                        mass_rate=x
                    ).is_valid,
                    convergence_tolerance=1e-3,
                    maximum_number_of_iterations=20,
                )
                result_max_std_rate_at_max_speed = _calculate_train_result_at_max_speed_given_std_rate_for_stream(
                    mass_rate=max_std_rate_m3_per_day_at_max_speed
                )
            else:
                logger.debug(
                    "There are no valid common std rate for VariableSpeedCompressorTrain, and ASV is not allowed."
                    "Infeasible solution. Returning max rate 0.0 (None)."
                )
                return 0.0
        else:
            min_std_rate_m3_per_day_at_max_speed = min_std_rate_for_stream_m3_per_day_at_max_speed
            result_min_std_rate_at_max_speed = result_min_std_rate_for_stream_at_max_speed

            # Ensuring that the maximum std rate at max speed is valid for the whole train.
            if not result_max_std_rate_for_stream_at_max_speed.is_valid:
                max_std_rate_m3_per_day_at_max_speed = maximize_x_given_boolean_condition_function(
                    x_min=min_std_rate_m3_per_day_at_max_speed,
                    x_max=max_std_rate_for_stream_m3_per_day_at_max_speed,
                    bool_func=lambda x: _calculate_train_result_at_max_speed_given_std_rate_for_stream(
                        std_rate_for_stream=x
                    ).is_valid,
                )
                result_max_std_rate_at_max_speed = _calculate_train_result_at_max_speed_given_std_rate_for_stream(
                    std_rate_for_stream=max_std_rate_m3_per_day_at_max_speed
                )
            else:
                max_std_rate_m3_per_day_at_max_speed = max_std_rate_for_stream_m3_per_day_at_max_speed
                result_max_std_rate_at_max_speed = result_max_std_rate_for_stream_at_max_speed

        # Solution scenario 1. Infeasible. Target pressure is too high.
        if result_min_std_rate_at_max_speed.discharge_pressure < target_discharge_pressure:
            return 0.0

        # Solution scenario 2. Solution is at maximum speed curve.
        elif target_discharge_pressure >= result_max_std_rate_for_stream_at_max_speed.discharge_pressure:
            result_std_rate = find_root(
                lower_bound=min_std_rate_m3_per_day_at_max_speed,
                upper_bound=max_std_rate_m3_per_day_at_max_speed,
                func=lambda x: _calculate_train_result_at_max_speed_given_std_rate_for_stream(
                    std_rate_for_stream=x
                ).discharge_pressure
                - target_discharge_pressure,
            )
            rate_to_return = result_std_rate * (1 - RATE_CALCULATION_TOLERANCE)

        # Solution 3: If solution not found along max speed curve,
        # run at max_mass_rate, but using the defined pressure control.
        elif (
            self.data_transfer_object.pressure_control is not None
            and self.calculate_compressor_train_given_rate_ps_pd_speed(
                speed=self.maximum_speed,
                inlet_pressure=suction_pressure,
                outlet_pressure=target_discharge_pressure,
                std_rates_std_m3_per_day_per_stream=np.asarray(
                    [
                        std_rates_std_m3_per_day_per_stream[i]
                        if i != stream_to_maximize
                        else max_std_rate_m3_per_day_at_max_speed
                        for i, _ in enumerate(self.streams)
                    ]
                ),
            ).is_valid
        ):
            rate_to_return = max_std_rate_m3_per_day_at_max_speed * (1 - RATE_CALCULATION_TOLERANCE)

        # Solution scenario 4. Solution at the "Stone wall".
        else:
            # Ensuring that the maximum mass rate at min speed is valid for the whole train.
            if not result_max_std_rate_for_stream_at_min_speed.is_valid:
                max_std_rate_m3_per_day_at_min_speed = maximize_x_given_boolean_condition_function(
                    x_min=EPSILON,
                    x_max=max_std_rate_for_stream_m3_per_day_at_min_speed,
                    bool_func=lambda x: _calculate_train_result_at_min_speed_given_std_rate_for_stream(
                        std_rate_for_stream=x
                    ).is_valid,
                )
                result_max_std_rate_at_min_speed = _calculate_train_result_at_min_speed_given_std_rate_for_stream(
                    std_rate_for_stream=max_std_rate_m3_per_day_at_min_speed
                )
            else:
                # max_std_rate_m3_per_day_at_min_speed = max_std_rate_for_stream_m3_per_day_at_min_speed
                result_max_std_rate_at_min_speed = result_max_std_rate_for_stream_at_min_speed

            if (
                result_max_std_rate_at_max_speed.discharge_pressure
                >= target_discharge_pressure
                >= result_max_std_rate_at_min_speed.discharge_pressure
            ):
                result_speed = find_root(
                    lower_bound=self.minimum_speed,
                    upper_bound=self.maximum_speed,
                    func=lambda x: _calculate_train_result_given_speed_at_stone_wall(speed=x)[1].discharge_pressure
                    - target_discharge_pressure,
                )
                (
                    max_valid_std_rate_m3_per_day,
                    compressor_train_result,
                ) = _calculate_train_result_given_speed_at_stone_wall(speed=result_speed)

                rate_to_return = max_valid_std_rate_m3_per_day * (1 - RATE_CALCULATION_TOLERANCE)

            # Solution scenario 5. Too high pressure even at min speed and max flow rate.
            elif result_max_std_rate_at_min_speed.discharge_pressure > target_discharge_pressure:
                # Todo: We could add additional functionality where the user can use to control what happens below
                #    minimum speed, such as ASV, choke, etc.
                return 0.0
            else:
                msg = "You should not end up here. Please contact eCalc support."
                logger.exception(msg)
                raise IllegalStateException(msg)

        # Check that rate_to_return, suction_pressure and discharge_pressure does not require too much power.
        # If so, reduce rate such that power comes below maximum power
        std_rates_std_m3_per_day_per_stream[stream_to_maximize] = rate_to_return
        if not self.data_transfer_object.maximum_power:
            return rate_to_return
        elif (
            self.evaluate_rate_ps_pd(
                rate=np.asarray([std_rates_std_m3_per_day_per_stream]),
                suction_pressure=np.asarray([suction_pressure]),
                discharge_pressure=np.asarray([target_discharge_pressure]),
            ).power_megawatt[0]
            > self.data_transfer_object.maximum_power
        ):
            # check if minimum_rate gives too high power consumption
            std_rates_std_m3_per_day_per_stream[stream_to_maximize] = EPSILON
            result_with_minimum_rate = self.evaluate_rate_ps_pd(
                rate=np.asarray([std_rates_std_m3_per_day_per_stream]),
                suction_pressure=np.asarray([suction_pressure]),
                discharge_pressure=np.asarray([target_discharge_pressure]),
            )
            if result_with_minimum_rate.power_megawatt[0] > self.data_transfer_object.maximum_power:
                return 0.0  # can't find solution
            else:
                std_rate_with_maximum_power = find_root(
                    lower_bound=result_with_minimum_rate.rate_sm3_day[stream_to_maximize],
                    upper_bound=rate_to_return,
                    func=lambda x: self.evaluate_rate_ps_pd(
                        rate=np.asarray(
                            [
                                std_rates_std_m3_per_day_per_stream[i] if i != stream_to_maximize else x
                                for i, _ in enumerate(self.streams)
                            ]
                        ),
                        suction_pressure=np.asarray([suction_pressure]),
                        discharge_pressure=np.asarray([target_discharge_pressure]),
                    ).power[0]
                    - self.data_transfer_object.maximum_power * (1 - POWER_CALCULATION_TOLERANCE),
                    relative_convergence_tolerance=1e-3,
                    maximum_number_of_iterations=20,
                )
                return std_rate_with_maximum_power
        else:
            return rate_to_return

    def evaluate_rate_ps_pint_pd(
        self,
        rate: NDArray[np.float64],
        suction_pressure: NDArray[np.float64],
        intermediate_pressure: NDArray[np.float64],
        discharge_pressure: NDArray[np.float64],
    ) -> CompressorTrainResult:
        """Train where some intermediate pressure is also met in addition to discharge pressure
        First, the train is split into two models, one before the intermediate and one after and the speed required for
        both these sub model trains are evaluated. Then the speed is set to the largest of these two, such that the
        pressure requirements can be met.
        Then, the train which required a lower speed to meet the pressures set, can be set up as a single speed train
        model where one of three methods to decrease the resulting pressure is chosen. The method to choose, will be
        dependent on the equipment available on the installation. One is upstream choking, one is downstream choking and
        the final is using asv, then where the asv (actual) rate is balanced between the stages (to mimic balanced ASV
        openings. Equal ASV openings will not result in the same ASV rate, but balanced asv rates is still assumed to be
        a good enough simplification of equal ASV openings.

        :param rate: rates in sm3/day for each stream in the compressor train
        :param suction_pressure: suction pressure in bara at inlet of first compressor in train
        :param intermediate_pressure: pressure at intermediate stage in bara
        :param discharge_pressure: discharge pressure in bara at outlet of last compressor in train
        """
        self._check_intermediate_pressure_stage_number_is_valid(
            _stage_number_intermediate_pressure=self.data_transfer_object.stage_number_interstage_pressure,
            number_of_stages=len(self.stages),
        )
        (
            rate,
            suction_pressure,
            discharge_pressure,
            intermediate_pressure,
            input_failure_status,
        ) = validate_model_input(
            rate=rate,
            suction_pressure=suction_pressure,
            discharge_pressure=discharge_pressure,
            intermediate_pressure=intermediate_pressure,
        )
        logger.debug(
            f"Evaluating {type(self).__name__} given suction pressure, discharge pressure, "
            "and an inter-stage pressure."
        )
        # Iterate over input points, calculate one by one
        train_results = []
        for (
            time_step,
            (
                suction_pressure_this_time_step,
                intermediate_pressure_this_time_step,
                discharge_pressure_this_time_step,
            ),
        ) in enumerate(zip(suction_pressure, intermediate_pressure, discharge_pressure)):
            std_rates_std_m3_per_day_per_stream_this_time_step = (
                self.check_that_ingoing_streams_are_larger_than_or_equal_to_outgoing_streams(rate[:, time_step])
            )
            inlet_rates_this_time_step = [
                std_rates_std_m3_per_day_per_stream_this_time_step[i]
                for (i, stream) in enumerate(self.streams)
                if stream.is_inlet_stream
            ]
            # Enough with one positive ingoing stream. Compressors with possible zero rates will recirculate
            positive_ingoing_streams = list(filter(lambda x: x > 0, list(inlet_rates_this_time_step)))
            if not any(positive_ingoing_streams):
                train_result = CompressorTrainResultSingleTimeStep.create_empty(number_of_stages=len(self.stages))
                train_results.append(train_result)
            else:
                compressor_train_result = self.find_and_calculate_for_compressor_train_with_two_pressure_requirements(
                    stage_number_for_intermediate_pressure_target=self.data_transfer_object.stage_number_interstage_pressure,
                    std_rates_std_m3_per_day_per_stream=std_rates_std_m3_per_day_per_stream_this_time_step,
                    suction_pressure=suction_pressure_this_time_step,
                    intermediate_pressure_target=intermediate_pressure_this_time_step,
                    discharge_pressure_target=discharge_pressure_this_time_step,
                    pressure_control_first_part=self.data_transfer_object.pressure_control_first_part,
                    pressure_control_last_part=self.data_transfer_object.pressure_control_last_part,
                )
                train_results.append(compressor_train_result)

        power_mw = np.array([time_step.power_megawatt for time_step in train_results])
        power_mw_adjusted = np.where(
            power_mw > 0, power_mw + self.data_transfer_object.energy_usage_adjustment_constant, power_mw
        )

        for i, train_result in enumerate(train_results):
            if input_failure_status[i] is not ModelInputFailureStatus.NO_FAILURE:
                train_result.failure_status = input_failure_status[i]

        return CompressorTrainResult(
            energy_usage=list(power_mw_adjusted),
            energy_usage_unit=Unit.MEGA_WATT,
            power=list(power_mw_adjusted),
            power_unit=Unit.MEGA_WATT,
            stage_results=CompressorTrainResultSingleTimeStep.from_result_list_to_dto(
                result_list=train_results,
                compressor_charts=[stage.compressor_chart.data_transfer_object for stage in self.stages],
            ),
            rate_sm3_day=cast(list, rate.tolist()),
            failure_status=[t.failure_status for t in train_results],
        )

    def calculate_compressor_train_given_rate_ps_speed(
        self,
        std_rates_std_m3_per_day_per_stream: NDArray[np.float64],
        inlet_pressure_bara: float,
        speed: float,
        asv_rate_fraction: float = 0.0,
        asv_additional_mass_rate: float = 0.0,
    ) -> CompressorTrainResultSingleTimeStep:
        """Calculate compressor train result given inlet conditions and speed
        Returns outlet_stream from final compressor stage (since it may be different to the inlet stream due
        to potential multiple inlet streams) and results including conditions and calculations for each stage and power.

        This function can be called in three different ways

        1) In a compressor train without an intermediate pressure target. Self.stream[0] will then be taken as the inlet
           stream to the compressor train

        2) As the first subtrain in a compressor train with an intermediate pressure target. Self.stream[0] will then be
           taken as the inlet stream to the compressor train

        3) As the last subtrain in a compressor train with an intermediate pressure target. If present, Self.stream[0]
           will then be a stream leaving/entering the compressor train, while self.inlet_fluid will describe the fluid
           coming out of the first subtrain (mass_rate_kg_per_hour_per_stage[0] will contain the corresponding
           mass rate).

        :param std_rates_std_m3_per_day_per_stream:
        :param inlet_pressure_bara: [bara]
        :param speed: [rpm]
        :param asv_rate_fraction:
        :param asv_additional_mass_rate:

        """
        stage_results = []
        inlet_stream = self.streams[0].fluid.get_fluid_stream(
            pressure_bara=inlet_pressure_bara,
            temperature_kelvin=self.stages[0].inlet_temperature_kelvin,
        )
        mass_rate_this_stage_kg_per_hour = inlet_stream.standard_rate_to_mass_rate(
            std_rates_std_m3_per_day_per_stream[0]
        )
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
                    std_rates_std_m3_per_day_per_stream[stream_number]
                )
            for stream_number in self.inlet_stream_connected_to_stage.get(stage_number):
                if stream_number > 0:
                    # Flash at outlet temperature or inlet temperature next stage? Must assume same temperature.
                    # Currently using outlet temperature
                    additional_inlet_stream = self.streams[stream_number].fluid.get_fluid_stream(
                        pressure_bara=inlet_stream.pressure_bara,
                        temperature_kelvin=inlet_stream.temperature_kelvin,
                    )
                    mass_rate_additional_inlet_stream_kg_per_hour = additional_inlet_stream.standard_rate_to_mass_rate(
                        float(std_rates_std_m3_per_day_per_stream[stream_number])
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
                        f"{std_rates_std_m3_per_day_per_stream}."
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
                speed=speed,
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
        return CompressorTrainResultSingleTimeStep(
            stage_results=stage_results,
            speed=speed,
        )

    def calculate_compressor_train_given_rate_pd_speed(
        self,
        speed: float,
        outlet_pressure: float,
        std_rates_std_m3_per_day_per_stream: NDArray[np.float64],
        upper_bound_for_inlet_pressure: Optional[float] = None,
    ) -> CompressorTrainResultSingleTimeStep:
        if not upper_bound_for_inlet_pressure:
            upper_bound_for_inlet_pressure = outlet_pressure

        def _calculate_train_result_given_rate_ps_speed(
            _inlet_pressure: float,
        ) -> CompressorTrainResultSingleTimeStep:
            return self.calculate_compressor_train_given_rate_ps_speed(
                inlet_pressure_bara=_inlet_pressure,
                std_rates_std_m3_per_day_per_stream=np.asarray(std_rates_std_m3_per_day_per_stream),
                speed=speed,
            )

        choked_inlet_pressure = find_root(
            lower_bound=UnitConstants.STANDARD_PRESSURE_BARA
            + self.stages[0].pressure_drop_ahead_of_stage,  # Fixme: What is a sensible value here?
            upper_bound=upper_bound_for_inlet_pressure,
            func=lambda x: _calculate_train_result_given_rate_ps_speed(_inlet_pressure=x).discharge_pressure
            - outlet_pressure,
        )
        compressor_train_result = self.calculate_compressor_train_given_rate_ps_speed(
            speed=speed,
            std_rates_std_m3_per_day_per_stream=std_rates_std_m3_per_day_per_stream,
            inlet_pressure_bara=choked_inlet_pressure,
        )

        return compressor_train_result

    def calculate_compressor_train_given_rate_ps_pd_speed(
        self,
        speed: float,
        inlet_pressure: float,
        outlet_pressure: float,
        std_rates_std_m3_per_day_per_stream: NDArray[np.float64],
    ) -> CompressorTrainResultSingleTimeStep:
        # if full recirculation gives low enough pressure, iterate on asv_rate_fraction to reach the target
        def _calculate_train_result_given_rate_ps_speed_asv_rate_fraction(
            asv_rate_fraction: float,
        ) -> CompressorTrainResultSingleTimeStep:
            """Note that we use outside variables for clarity and to avoid class instances."""
            train_results_this_time_step = self.calculate_compressor_train_given_rate_ps_speed(
                std_rates_std_m3_per_day_per_stream=std_rates_std_m3_per_day_per_stream,
                inlet_pressure_bara=inlet_pressure,
                speed=speed,
                asv_rate_fraction=asv_rate_fraction,
            )
            return train_results_this_time_step

        if self.pressure_control in (
            FixedSpeedPressureControl.UPSTREAM_CHOKE,
            FixedSpeedPressureControl.DOWNSTREAM_CHOKE,
        ):
            # Checking for upstream choke also, to find if we are in a situation where upstream choking is feasible
            # (can inlet_pressure and speed give at least the required outlet_pressure)
            train_results = self.calculate_compressor_train_given_rate_ps_speed(
                std_rates_std_m3_per_day_per_stream=std_rates_std_m3_per_day_per_stream,
                inlet_pressure_bara=inlet_pressure,
                speed=speed,
            )
            if train_results.discharge_pressure * (1 + PRESSURE_CALCULATION_TOLERANCE) < outlet_pressure:
                # Should probably never end up here. This is just in case we do.
                train_results.failure_status = (
                    CompressorTrainCommonShaftFailureStatus.TARGET_DISCHARGE_PRESSURE_TOO_HIGH
                )
            elif self.pressure_control == FixedSpeedPressureControl.UPSTREAM_CHOKE:
                train_results = self.calculate_compressor_train_given_rate_pd_speed(
                    std_rates_std_m3_per_day_per_stream=std_rates_std_m3_per_day_per_stream,
                    outlet_pressure=outlet_pressure,
                    speed=speed,
                    upper_bound_for_inlet_pressure=inlet_pressure,
                )
                # Set pressure before upstream choking to the given inlet pressure
                train_results.stage_results[0].inlet_pressure_before_choking = (
                    inlet_pressure - self.stages[0].pressure_drop_ahead_of_stage
                )
            elif self.pressure_control == FixedSpeedPressureControl.DOWNSTREAM_CHOKE:
                choked_stage_results = deepcopy(train_results.stage_results[-1])
                if (
                    train_results.failure_status
                    == CompressorTrainCommonShaftFailureStatus.TARGET_DISCHARGE_PRESSURE_TOO_LOW
                    and outlet_pressure >= UnitConstants.STANDARD_PRESSURE_BARA
                ):
                    train_results.failure_status = None

                # The order is important here to keep the old pressure before choking.
                choked_stage_results.pressure_is_choked = True
                choked_stage_results.outlet_pressure_before_choking = float(choked_stage_results.discharge_pressure)
                choked_stage_results.outlet_stream.pressure_bara = outlet_pressure
                train_results.stage_results[-1] = choked_stage_results

        elif self.pressure_control == FixedSpeedPressureControl.INDIVIDUAL_ASV_RATE:
            # first check if full recirculation gives low enough discharge pressure
            train_result_max_recirculation = self.calculate_compressor_train_given_rate_ps_speed(
                std_rates_std_m3_per_day_per_stream=std_rates_std_m3_per_day_per_stream,
                inlet_pressure_bara=inlet_pressure,
                speed=speed,
                asv_rate_fraction=1.0,
            )
            if not train_result_max_recirculation.discharge_pressure < outlet_pressure:
                train_result_max_recirculation.failure_status = (
                    CompressorTrainCommonShaftFailureStatus.TARGET_DISCHARGE_PRESSURE_TOO_LOW
                )
                msg = (
                    f"Compressor train with inlet pressure {inlet_pressure} and speed {speed} is not able"
                    f"to reach the required discharge pressure {outlet_pressure} even with full recirculation. "
                    f"Pressure control {self.pressure_control} not feasible."
                )
                logger.debug(msg)  # Todo: Consider fallback to upstream choke instead of failure?
                return train_result_max_recirculation

            result_asv_rate_margin = find_root(
                lower_bound=0.0,
                upper_bound=1.0,
                func=lambda x: _calculate_train_result_given_rate_ps_speed_asv_rate_fraction(
                    asv_rate_fraction=x
                ).discharge_pressure
                - outlet_pressure,
            )
            train_results = self.calculate_compressor_train_given_rate_ps_speed(
                std_rates_std_m3_per_day_per_stream=std_rates_std_m3_per_day_per_stream,
                inlet_pressure_bara=inlet_pressure,
                speed=speed,
                asv_rate_fraction=result_asv_rate_margin,
            )
        # For INDIVIDUAL_ASV_PRESSURE and COMMON_ASV current solution is making a single speed equivalent train
        # Hence, there is no possibility for multiple streams entering/leaving the compressor train (when this option
        # is used for interstage pressure the sub-trains may be without multiple streams
        elif self.pressure_control in (
            FixedSpeedPressureControl.INDIVIDUAL_ASV_PRESSURE,
            FixedSpeedPressureControl.COMMON_ASV,
        ):
            # Run as a single speed train with rate adjustment
            # Todo: not feasible if there is more than one stream going into compressor train?
            #       currently relying on only one stream entering the train controlled by
            #       asv and balanced pressure ratios
            (
                inlet_fluid_single_speed_train,
                updated_std_rates_std_m3_per_day_per_stream,
            ) = self._update_inlet_fluid_and_std_rates_for_last_subtrain(
                std_rates_std_m3_per_day_per_stream=std_rates_std_m3_per_day_per_stream,
                inlet_pressure=inlet_pressure,
            )

            if len(updated_std_rates_std_m3_per_day_per_stream) > 1:
                raise NotImplementedError(
                    "Making a single speed train using asv and balanced pressure ratios not implemented "
                    "when there are multiple streams entering the subtrain in question"
                )

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
                data_transfer_object=dto.SingleSpeedCompressorTrain(
                    fluid_model=inlet_fluid_single_speed_train.fluid_model,
                    stages=[
                        dto.CompressorStage(
                            compressor_chart=dto.SingleSpeedChart(
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
            single_speed_train_results = single_speed_train._evaluate_rate_ps_pd(
                rate=np.asarray(updated_std_rates_std_m3_per_day_per_stream),
                suction_pressure=np.asarray([inlet_pressure]),
                discharge_pressure=np.asarray([outlet_pressure]),
            )

            for train_result in single_speed_train_results:
                train_result.speed = speed
            # return CompressorTrainResultSingleTimeStep for first time step (should be only one here, really)
            train_results = single_speed_train_results[0]
        else:
            raise IllegalStateException(
                f"Pressure control {self.pressure_control} not supported, should be one of"
                f"{list(FixedSpeedPressureControl)}. Should not end up here, please contact support."
            )

        return train_results

    def _update_inlet_fluid_and_std_rates_for_last_subtrain(
        self,
        std_rates_std_m3_per_day_per_stream: NDArray[np.float64],
        inlet_pressure: float,
    ) -> Tuple[FluidStream, NDArray[np.float64]]:
        """ """
        # first make inlet stream from stream[0]
        inlet_stream = self.streams[0].fluid.get_fluid_stream(
            pressure_bara=inlet_pressure,
            temperature_kelvin=self.stages[0].inlet_temperature_kelvin,
        )
        inlet_std_rate = float(std_rates_std_m3_per_day_per_stream[0])
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
                    float(std_rates_std_m3_per_day_per_stream[stream_number])
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

        return updated_inlet_fluid, np.asarray(updated_std_rates_std_m3_per_day_per_stream)

    def find_and_calculate_for_compressor_train_with_two_pressure_requirements(
        self,
        stage_number_for_intermediate_pressure_target: int,
        std_rates_std_m3_per_day_per_stream: NDArray[np.float64],
        suction_pressure: float,
        intermediate_pressure_target: float,
        discharge_pressure_target: float,
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
        compressor_train_first_part, compressor_train_last_part = split_train_on_stage_number(
            compressor_train=self,
            stage_number=stage_number_for_intermediate_pressure_target,
            pressure_control_first_part=pressure_control_first_part,
            pressure_control_last_part=pressure_control_last_part,
        )

        inlet_pressure_first_part, outlet_pressure_first_part = suction_pressure, intermediate_pressure_target
        inlet_pressure_last_part, outlet_pressure_last_part = intermediate_pressure_target, discharge_pressure_target
        std_rates_first_part, std_rates_last_part = split_rates_on_stage_number(
            compressor_train=self,
            rates_per_stream=std_rates_std_m3_per_day_per_stream,
            stage_number=stage_number_for_intermediate_pressure_target,
        )
        compressor_train_results_first_part_with_optimal_speed_result = (
            compressor_train_first_part.calculate_shaft_speed_given_rate_ps_pd(
                std_rates_std_m3_per_day_per_stream=std_rates_first_part,
                suction_pressure=inlet_pressure_first_part,
                target_discharge_pressure=outlet_pressure_first_part,
                lower_bound_for_speed=self.minimum_speed,  # Only search for a solution within the bounds of the
                upper_bound_for_speed=self.maximum_speed,  # original, complete compressor train
            )
        )

        if self.data_transfer_object.calculate_max_rate:
            max_standard_rate_per_stream = [
                compressor_train_first_part._get_max_rate_for_single_stream_single_timestep(
                    suction_pressure=inlet_pressure_first_part,
                    target_discharge_pressure=outlet_pressure_first_part,
                    rate_per_stream=std_rates_first_part,
                    stream_to_maximize=stream_index,
                )
                for stream_index, _ in enumerate(compressor_train_first_part.streams)
            ]
        else:
            max_standard_rate_per_stream = [np.nan] * len(std_rates_first_part)

        # set self.inlet_fluid based on outlet_stream_first_part
        compressor_train_last_part.streams[0].fluid = FluidStream(  # filling the placeholder with the correct fluid
            fluid_model=dto.FluidModel(
                composition=compressor_train_results_first_part_with_optimal_speed_result.stage_results[
                    -1
                ].outlet_stream.composition,
                eos_model=compressor_train_results_first_part_with_optimal_speed_result.stage_results[
                    -1
                ].outlet_stream.eos_model,
            )
        )

        compressor_train_results_last_part_with_optimal_speed_result = (
            compressor_train_last_part.calculate_shaft_speed_given_rate_ps_pd(
                std_rates_std_m3_per_day_per_stream=std_rates_last_part,
                suction_pressure=inlet_pressure_last_part,
                target_discharge_pressure=outlet_pressure_last_part,
                lower_bound_for_speed=self.minimum_speed,
                upper_bound_for_speed=self.maximum_speed,
            )
        )

        if self.data_transfer_object.calculate_max_rate:
            for stream_index, _ in enumerate(compressor_train_last_part.streams):
                if stream_index > 0:
                    max_standard_rate_per_stream.append(
                        compressor_train_first_part._get_max_rate_for_single_stream_single_timestep(
                            suction_pressure=inlet_pressure_last_part,
                            target_discharge_pressure=outlet_pressure_last_part,
                            rate_per_stream=std_rates_last_part,
                            stream_to_maximize=stream_index,
                        )
                    )
        else:
            max_standard_rate_per_stream = max_standard_rate_per_stream + [np.nan] * len(std_rates_last_part[1:])
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
                compressor_train_last_part.calculate_compressor_train_given_rate_ps_pd_speed(
                    std_rates_std_m3_per_day_per_stream=std_rates_last_part,
                    speed=speed,
                    inlet_pressure=inlet_pressure_last_part,
                    outlet_pressure=outlet_pressure_last_part,
                )
            )
            compressor_train_results_to_return_first_part = (
                compressor_train_results_first_part_with_optimal_speed_result
            )
            compressor_train_results_to_return_last_part = compressor_train_results_last_part_with_pressure_control

        else:
            speed = compressor_train_results_last_part_with_optimal_speed_result.speed
            compressor_train_results_first_part_with_pressure_control = (
                compressor_train_first_part.calculate_compressor_train_given_rate_ps_pd_speed(
                    std_rates_std_m3_per_day_per_stream=std_rates_first_part,
                    speed=speed,
                    inlet_pressure=inlet_pressure_first_part,
                    outlet_pressure=outlet_pressure_first_part,
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

        return CompressorTrainResultSingleTimeStep(
            speed=speed,
            stage_results=compressor_train_results_to_return_stage_results,
            failure_status=compressor_train_results_to_return_first_part.failure_status
            or compressor_train_results_to_return_last_part.failure_status,
        )

    def set_fluid_to_recirculate_in_stage_when_inlet_rate_is_zero(
        self, stage_number: int, fluid_stream: FluidStream
    ) -> None:
        """Keep track of what fluid passes through each compressor stage in the compressor train at a given calculation
        step. This is done in case of the possibility of having a zero inlet rate at the next calculation step when
        adding/subtracting ingoing/outgoing streams.

        Args:
            stage_number: The stage number (zero index)
            fluid_stream: The fluid stream passing through compressor stage number <stage_number>
        """
        self.fluid_to_recirculate_in_stage_when_inlet_rate_is_zero[stage_number] = fluid_stream

    def get_fluid_to_recirculate_in_stage_when_inlet_rate_is_zero(self, stage_number: int) -> FluidStream:
        """Retrieve the fluid that passed through a given compressor stage in the compressor train at the previous
        calculation step.

        Arge:
            stage_number: The stage number (zero index)

        """
        return self.fluid_to_recirculate_in_stage_when_inlet_rate_is_zero[stage_number]


def split_rates_on_stage_number(
    compressor_train: VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures,
    rates_per_stream: NDArray[np.float64],
    stage_number: int,
) -> Tuple[NDArray[np.float64], NDArray[np.float64]]:
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

    return np.asarray(rates_first_part), np.asarray(rates_last_part)


def split_train_on_stage_number(
    compressor_train: VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures,
    stage_number: int,
    pressure_control_first_part: Optional[FixedSpeedPressureControl] = None,
    pressure_control_last_part: Optional[FixedSpeedPressureControl] = None,
) -> Tuple[
    VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures,
    VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures,
]:
    """Split train into two and calculate minimum speed to reach required pressures.

    :param compressor_train: Variable speed compressor train
    :param stage_number:
    :return:
    """
    first_part_data_transfer_object = compressor_train.data_transfer_object.model_copy()
    last_part_data_transfer_object = compressor_train.data_transfer_object.model_copy()
    first_part_data_transfer_object.stages = first_part_data_transfer_object.stages[:stage_number]
    last_part_data_transfer_object.stages = last_part_data_transfer_object.stages[stage_number:]
    first_part_data_transfer_object.pressure_control = pressure_control_first_part
    last_part_data_transfer_object.pressure_control = pressure_control_last_part

    compressor_train_first_part = VariableSpeedCompressorTrainCommonShaftMultipleStreamsAndPressures(
        streams=[stream for stream in compressor_train.streams if stream.connected_to_stage_no < stage_number],
        data_transfer_object=cast(
            dto.VariableSpeedCompressorTrainMultipleStreamsAndPressures, first_part_data_transfer_object
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
            dto.VariableSpeedCompressorTrainMultipleStreamsAndPressures, last_part_data_transfer_object
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
