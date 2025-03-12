from copy import deepcopy
from typing import cast

import numpy as np
from numpy.typing import NDArray

from libecalc.common.errors.exceptions import EcalcError, IllegalStateException
from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl
from libecalc.common.fluid import FluidModel
from libecalc.common.fluid import FluidStream as FluidStreamDTO
from libecalc.common.logger import logger
from libecalc.common.serializable_chart import SingleSpeedChartDTO
from libecalc.common.units import Unit, UnitConstants
from libecalc.domain.process.core import ModelInputFailureStatus, validate_model_input
from libecalc.domain.process.core.compressor.results import CompressorTrainResultSingleTimeStep
from libecalc.domain.process.core.compressor.train.base import CompressorTrainModel
from libecalc.domain.process.core.compressor.train.fluid import FluidStream
from libecalc.domain.process.core.compressor.train.single_speed_compressor_train_common_shaft import (
    SingleSpeedCompressorTrainCommonShaft,
)
from libecalc.domain.process.core.compressor.train.stage import CompressorTrainStage
from libecalc.domain.process.core.compressor.train.types import (
    FluidStreamObjectForMultipleStreams,
)
from libecalc.domain.process.core.compressor.train.utils.numeric_methods import (
    find_root,
    maximize_x_given_boolean_condition_function,
)
from libecalc.domain.process.core.compressor.train.utils.variable_speed_compressor_train_common_shaft import (
    get_single_speed_equivalent,
)
from libecalc.domain.process.core.results import CompressorTrainResult
from libecalc.domain.process.core.results.compressor import (
    TargetPressureStatus,
)
from libecalc.domain.process.dto import (
    CompressorStage,
    SingleSpeedCompressorTrain,
    VariableSpeedCompressorTrainMultipleStreamsAndPressures,
)

EPSILON = 1e-5


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
    ) -> list[CompressorTrainResultSingleTimeStep]:
        # Iterate over input points, calculate one by one
        train_results = []
        for time_step, (
            suction_pressure_this_time_step,
            discharge_pressure_this_time_step,
        ) in enumerate(zip(suction_pressure, discharge_pressure)):
            self.target_suction_pressure = suction_pressure_this_time_step
            self.target_discharge_pressure = discharge_pressure_this_time_step
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

    def convert_to_rates_for_each_compressor_train_stages(self, rates_per_stream: NDArray[np.float64]) -> list[float]:
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
        lower_bound_for_speed: float | None = None,
        upper_bound_for_speed: float | None = None,
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

        if not train_result_for_maximum_speed.within_capacity:
            # will not find valid result - the rate is above maximum rate, return invalid results at maximum speed
            return train_result_for_maximum_speed
        if not train_result_for_minimum_speed.within_capacity:
            # rate is above maximum rate for minimum speed. Find the lowest minimum speed which gives a valid result
            minimum_speed = -maximize_x_given_boolean_condition_function(
                x_min=-self.maximum_speed,
                x_max=-self.minimum_speed,
                bool_func=lambda x: _calculate_train_result_given_rate_ps_speed(_speed=-x).within_capacity,
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
                return train_result_for_minimum_speed
        # Solution 3, target discharge pressure is too high
        else:
            return train_result_for_maximum_speed

    def get_max_standard_rate(
        self,
        suction_pressures: NDArray[np.float64] | None = None,
        discharge_pressures: NDArray[np.float64] | None = None,
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
                self.target_suction_pressure = suction_pressure
                self.target_discharge_pressure = discharge_pressure
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
    ) -> float:
        """NB: Constraining to calculating maximum_rate for ingoing streams for now - the need is to figure out how much rate
        can be added.

        """
        stream_to_maximize_connected_to_stage_no = self.streams[stream_to_maximize].connected_to_stage_no

        # if it is not an ingoing stream --> currently no calculations done
        # Fixme: what should be returned? 0.0, NaN or something else?
        if not self.streams[stream_to_maximize].is_inlet_stream:
            return 0.0

        std_rates_std_m3_per_day_per_stream = rate_per_stream.copy()

        def _calculate_train_result(std_rate_for_stream: float) -> CompressorTrainResultSingleTimeStep:
            """Partial function of self.calculate_compressor_train_given_rate_ps_speed
            where we only pass std_rate_per_stream and speed.
            """
            std_rates_std_m3_per_day_per_stream[stream_to_maximize] = std_rate_for_stream
            return self.calculate_shaft_speed_given_rate_ps_pd(
                std_rates_std_m3_per_day_per_stream=std_rates_std_m3_per_day_per_stream,
                suction_pressure=suction_pressure,
                target_discharge_pressure=target_discharge_pressure,
            )

        train_result = self.calculate_shaft_speed_given_rate_ps_pd(
            std_rates_std_m3_per_day_per_stream=std_rates_std_m3_per_day_per_stream,
            suction_pressure=suction_pressure,
            target_discharge_pressure=target_discharge_pressure,
        )
        if not train_result.is_valid:
            zero_stream_result = _calculate_train_result(std_rate_for_stream=EPSILON)
            if not zero_stream_result.is_valid:
                return 0.0
            else:
                return maximize_x_given_boolean_condition_function(
                    x_min=0.0,
                    x_max=float(rate_per_stream[stream_to_maximize]),
                    bool_func=lambda x: _calculate_train_result(std_rate_for_stream=x).is_valid,
                )
        else:
            max_rate_is_larger_than = std_rates_std_m3_per_day_per_stream[stream_to_maximize]
        while train_result.is_valid:
            max_rate_is_larger_than = train_result.stage_results[
                stream_to_maximize_connected_to_stage_no
            ].standard_rate_asv_corrected_sm3_per_day
            std_rates_std_m3_per_day_per_stream[stream_to_maximize] = max_rate_is_larger_than * 2
            train_result = self.calculate_shaft_speed_given_rate_ps_pd(
                std_rates_std_m3_per_day_per_stream=std_rates_std_m3_per_day_per_stream,
                suction_pressure=suction_pressure,
                target_discharge_pressure=target_discharge_pressure,
            )
        return maximize_x_given_boolean_condition_function(
            x_min=float(max_rate_is_larger_than),
            x_max=float(max_rate_is_larger_than * 2),
            bool_func=lambda x: _calculate_train_result(std_rate_for_stream=x).is_valid,
        )

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
            self.target_suction_pressure = suction_pressure_this_time_step
            self.target_intermediate_pressure = intermediate_pressure_this_time_step
            self.target_discharge_pressure = discharge_pressure_this_time_step
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
            power_mw > 0,
            power_mw * self.data_transfer_object.energy_usage_adjustment_factor
            + self.data_transfer_object.energy_usage_adjustment_constant,
            power_mw,
        )

        inlet_stream, outlet_stream, stage_results = CompressorTrainResultSingleTimeStep.from_result_list_to_dto(
            result_list=train_results,
            compressor_charts=[stage.compressor_chart.data_transfer_object for stage in self.stages],
        )
        return CompressorTrainResult(
            inlet_stream_condition=inlet_stream,
            outlet_stream_condition=outlet_stream,
            energy_usage=list(power_mw_adjusted),
            energy_usage_unit=Unit.MEGA_WATT,
            power=list(power_mw_adjusted),
            power_unit=Unit.MEGA_WATT,
            stage_results=stage_results,
            rate_sm3_day=cast(list, rate.tolist()),
            failure_status=[
                input_failure_status[i]
                if input_failure_status[i] is not ModelInputFailureStatus.NO_FAILURE
                else t.failure_status
                for i, t in enumerate(train_results)
            ],
            target_pressure_status=[t.target_pressure_status for t in train_results],
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
        train_inlet_stream = inlet_stream = self.streams[0].fluid.get_fluid_stream(
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

        # check if target pressures are met
        target_pressure_status = self.check_target_pressures(
            calculated_suction_pressure=train_inlet_stream.pressure_bara,
            calculated_discharge_pressure=previous_outlet_stream.pressure_bara,
        )

        return CompressorTrainResultSingleTimeStep(
            inlet_stream=FluidStreamDTO.from_fluid_domain_object(fluid_stream=train_inlet_stream),
            outlet_stream=FluidStreamDTO.from_fluid_domain_object(fluid_stream=previous_outlet_stream),
            stage_results=stage_results,
            speed=speed,
            target_pressure_status=target_pressure_status,
        )

    def calculate_compressor_train_given_rate_pd_speed(
        self,
        speed: float,
        outlet_pressure: float,
        std_rates_std_m3_per_day_per_stream: NDArray[np.float64],
        upper_bound_for_inlet_pressure: float | None = None,
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
            train_result = self.calculate_compressor_train_given_rate_ps_speed(
                std_rates_std_m3_per_day_per_stream=std_rates_std_m3_per_day_per_stream,
                inlet_pressure_bara=inlet_pressure,
                speed=speed,
            )
            if self.pressure_control == FixedSpeedPressureControl.UPSTREAM_CHOKE:
                train_result = self.calculate_compressor_train_given_rate_pd_speed(
                    std_rates_std_m3_per_day_per_stream=std_rates_std_m3_per_day_per_stream,
                    outlet_pressure=outlet_pressure,
                    speed=speed,
                    upper_bound_for_inlet_pressure=inlet_pressure,
                )
                if train_result.target_pressure_status == TargetPressureStatus.BELOW_TARGET_SUCTION_PRESSURE:
                    new_inlet_stream = FluidStream(
                        fluid_model=train_result.inlet_stream,
                        pressure_bara=inlet_pressure,
                        temperature_kelvin=train_result.inlet_stream.temperature_kelvin,
                    )
                    train_result.inlet_stream = FluidStreamDTO.from_fluid_domain_object(fluid_stream=new_inlet_stream)
                    train_result.target_pressure_status = self.check_target_pressures(
                        calculated_suction_pressure=train_result.inlet_stream.pressure_bara,
                        calculated_discharge_pressure=train_result.outlet_stream.pressure_bara,
                    )
            elif self.pressure_control == FixedSpeedPressureControl.DOWNSTREAM_CHOKE:
                if train_result.target_pressure_status == TargetPressureStatus.ABOVE_TARGET_DISCHARGE_PRESSURE:
                    new_outlet_stream = FluidStream(
                        fluid_model=train_result.outlet_stream,
                        pressure_bara=outlet_pressure,
                        temperature_kelvin=train_result.outlet_stream.temperature_kelvin,
                    )
                    train_result.outlet_stream = FluidStreamDTO.from_fluid_domain_object(fluid_stream=new_outlet_stream)
                    train_result.target_pressure_status = self.check_target_pressures(
                        calculated_suction_pressure=train_result.inlet_stream.pressure_bara,
                        calculated_discharge_pressure=train_result.outlet_stream.pressure_bara,
                    )

        elif self.pressure_control == FixedSpeedPressureControl.INDIVIDUAL_ASV_RATE:
            # first check if there is room for recirculation
            train_result_no_recirculation = self.calculate_compressor_train_given_rate_ps_speed(
                std_rates_std_m3_per_day_per_stream=std_rates_std_m3_per_day_per_stream,
                inlet_pressure_bara=inlet_pressure,
                speed=speed,
            )
            if not train_result_no_recirculation.within_capacity:
                return train_result_no_recirculation
            # then check if full recirculation gives low enough discharge pressure
            train_result_max_recirculation = self.calculate_compressor_train_given_rate_ps_speed(
                std_rates_std_m3_per_day_per_stream=std_rates_std_m3_per_day_per_stream,
                inlet_pressure_bara=inlet_pressure,
                speed=speed,
                asv_rate_fraction=1.0,
            )
            if not train_result_max_recirculation.discharge_pressure < outlet_pressure:
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
            train_result = self.calculate_compressor_train_given_rate_ps_speed(
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
            single_speed_train_results = single_speed_train._evaluate_rate_ps_pd(
                rate=np.asarray(updated_std_rates_std_m3_per_day_per_stream),
                suction_pressure=np.asarray([inlet_pressure]),
                discharge_pressure=np.asarray([outlet_pressure]),
            )

            for train_result in single_speed_train_results:
                train_result.speed = speed
            # return CompressorTrainResultSingleTimeStep for first time step (should be only one here, really)
            train_result = single_speed_train_results[0]
        else:
            raise IllegalStateException(
                f"Pressure control {self.pressure_control} not supported, should be one of"
                f"{list(FixedSpeedPressureControl)}. Should not end up here, please contact support."
            )

        return train_result

    def _update_inlet_fluid_and_std_rates_for_last_subtrain(
        self,
        std_rates_std_m3_per_day_per_stream: NDArray[np.float64],
        inlet_pressure: float,
    ) -> tuple[FluidStream, NDArray[np.float64]]:
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
        compressor_train_first_part.target_suction_pressure = inlet_pressure_first_part
        compressor_train_first_part.target_discharge_pressure = outlet_pressure_first_part
        compressor_train_last_part.target_suction_pressure = inlet_pressure_last_part
        compressor_train_last_part.target_discharge_pressure = outlet_pressure_last_part
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
            fluid_model=FluidModel(
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
            target_pressure_status=target_pressure_status,
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
) -> tuple[NDArray[np.float64], NDArray[np.float64]]:
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
