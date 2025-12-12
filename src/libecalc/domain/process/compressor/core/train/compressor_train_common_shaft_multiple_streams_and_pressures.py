import math
from copy import deepcopy

import numpy as np
from numpy._typing import NDArray

from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl
from libecalc.common.logger import logger
from libecalc.domain.component_validation_error import ProcessChartTypeValidationException
from libecalc.domain.process.compressor.core.results import CompressorTrainResultSingleTimeStep
from libecalc.domain.process.compressor.core.train.compressor_train_common_shaft import CompressorTrainCommonShaft
from libecalc.domain.process.compressor.core.train.stage import CompressorTrainStage
from libecalc.domain.process.compressor.core.train.types import FluidStreamObjectForMultipleStreams
from libecalc.domain.process.compressor.core.train.utils.common import EPSILON
from libecalc.domain.process.core.results.compressor import TargetPressureStatus
from libecalc.domain.process.entities.shaft import Shaft, VariableSpeedShaft
from libecalc.domain.process.value_objects.fluid_stream import FluidStream
from libecalc.domain.process.value_objects.fluid_stream.fluid_factory import FluidFactoryInterface


class CompressorTrainCommonShaftMultipleStreamsAndPressures(CompressorTrainCommonShaft):
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
        streams: list[FluidStreamObjectForMultipleStreams],
        energy_usage_adjustment_constant: float,
        energy_usage_adjustment_factor: float,
        stages: list[CompressorTrainStage],
        shaft: Shaft,
        calculate_max_rate: bool = False,
        maximum_power: float | None = None,
        pressure_control: FixedSpeedPressureControl | None = None,
        stage_number_interstage_pressure: int | None = None,
    ):
        logger.debug(f"Creating {type(self).__name__} with\n" f"n_stages: {len(stages)} and n_streams: {len(streams)}")
        super().__init__(
            energy_usage_adjustment_constant=energy_usage_adjustment_constant,
            energy_usage_adjustment_factor=energy_usage_adjustment_factor,
            stages=stages,
            shaft=shaft,
            maximum_power=maximum_power,
            pressure_control=pressure_control,
            calculate_max_rate=calculate_max_rate,
            stage_number_interstage_pressure=stage_number_interstage_pressure,
        )
        if pressure_control and not isinstance(pressure_control, FixedSpeedPressureControl):
            raise TypeError(f"pressure_control must be of type FixedSpeedPressureControl, got {type(pressure_control)}")
        self._validate_stages(stages)
        self.streams = streams
        self.number_of_compressor_streams = len(self.streams)

        for i, stream in enumerate(self.streams):
            if stream.is_inlet_stream:
                self.inlet_stream_connected_to_stage[stream.connected_to_stage_no].append(i)
            else:
                self.outlet_stream_connected_to_stage[stream.connected_to_stage_no].append(i)

    @property
    def pressure_control_first_part(self) -> FixedSpeedPressureControl:
        return (
            self.stages[self.stage_number_interstage_pressure].interstage_pressure_control.upstream_pressure_control
            if self.stage_number_interstage_pressure
            else None
        )

    @property
    def pressure_control_last_part(self) -> FixedSpeedPressureControl:
        return (
            self.stages[self.stage_number_interstage_pressure].interstage_pressure_control.downstream_pressure_control
            if self.stage_number_interstage_pressure
            else None
        )

    def set_evaluation_input(
        self,
        rate: NDArray[np.float64],
        fluid_factory: FluidFactoryInterface | list[FluidFactoryInterface],
        suction_pressure: NDArray[np.float64],
        discharge_pressure: NDArray[np.float64],
        intermediate_pressure: NDArray[np.float64] | None = None,
    ):
        has_interstage_pressure = any(stage.interstage_pressure_control is not None for stage in self.stages)
        if has_interstage_pressure and intermediate_pressure is None:
            raise ValueError("Energy model requires interstage control pressure to be defined")
        if not has_interstage_pressure and intermediate_pressure is not None:
            raise ValueError("Energy model does not accept interstage control pressure to be defined")
        super().set_evaluation_input(
            rate=rate,
            suction_pressure=suction_pressure,
            discharge_pressure=discharge_pressure,
            intermediate_pressure=intermediate_pressure,
            fluid_factory=fluid_factory,
        )

    def _validate_stages(self, stages: list[CompressorTrainStage]):
        min_speed_per_stage = []
        max_speed_per_stage = []
        for stage in stages:
            max_speed_per_stage.append(stage.compressor.compressor_chart.maximum_speed)
            min_speed_per_stage.append(stage.compressor.compressor_chart.minimum_speed)

        if max(min_speed_per_stage) > min(max_speed_per_stage):
            msg = "Variable speed compressors in compressor train have incompatible compressor charts."
            f" Stage {min_speed_per_stage.index(max(min_speed_per_stage)) + 1}'s minimum speed is higher"
            f" than max speed of stage {max_speed_per_stage.index(min(max_speed_per_stage)) + 1}"

            raise ProcessChartTypeValidationException(message=str(msg))

    def find_and_calculate_for_compressor_train_with_two_pressure_requirements(
        self,
        stage_number_for_intermediate_pressure_target: int | None,
        streams: list[FluidStream | float],
        boundary_conditions: dict[str, float],
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
            streams (list[FluidStream|float]): List of fluid streams or rates associated with the compressor train.
            boundary_conditions (dict[str, float]): Dictionary containing boundary conditions such as discharge pressure and interstage pressure.
            pressure_control_first_part (FixedSpeedPressureControl): Pressure control strategy for the first sub-train.
            pressure_control_last_part (FixedSpeedPressureControl): Pressure control strategy for the second sub-train.

        Returns:
            CompressorTrainResultSingleTimeStep: The combined result of the two sub-trains, including stage results,
            inlet/outlet streams, speed, and pressure status.
        """
        # This method requires stream_rates to be set for splitting operations
        target_discharge_pressure = boundary_conditions.get("discharge_pressure", None)
        target_interstage_pressure = boundary_conditions.get("interstage_pressure", None)

        assert target_discharge_pressure is not None
        assert target_interstage_pressure is not None
        assert stage_number_for_intermediate_pressure_target is not None

        # Split train into two and calculate minimum speed to reach required pressures
        compressor_train_first_part, compressor_train_last_part = split_train_on_stage_number(
            compressor_train=self,
            stage_number=stage_number_for_intermediate_pressure_target,
            pressure_control_first_part=pressure_control_first_part,
            pressure_control_last_part=pressure_control_last_part,
        )

        streams_first_part, streams_last_part = split_streams_on_stage_number(
            compressor_train=self,
            streams=streams,
            stage_number=stage_number_for_intermediate_pressure_target,
        )
        boundary_conditions_first_part = {
            "discharge_pressure": target_interstage_pressure,
        }
        boundary_conditions_last_part = {
            "discharge_pressure": target_discharge_pressure,
        }

        compressor_train_first_part.find_fixed_shaft_speed(
            streams=streams_first_part,
            boundary_conditions=boundary_conditions_first_part,
            lower_bound_for_speed=self.minimum_speed,  # Only search for a solution within the bounds of the
            upper_bound_for_speed=self.maximum_speed,  # original, complete compressor train
        )
        if math.isclose(compressor_train_first_part.shaft.get_speed(), self.minimum_speed, rel_tol=EPSILON):
            compressor_train_results_first_part_with_optimal_speed_result = (
                compressor_train_first_part.evaluate_with_pressure_control(
                    streams=streams_first_part,
                    boundary_conditions=boundary_conditions_first_part,
                )
            )
        else:
            compressor_train_results_first_part_with_optimal_speed_result = (
                compressor_train_first_part.calculate_compressor_train(
                    streams=streams_first_part,
                    boundary_conditions=boundary_conditions_first_part,
                )
            )

        # set self.inlet_fluid based on outlet_stream_first_part
        streams_last_part[0] = compressor_train_results_first_part_with_optimal_speed_result.outlet_stream

        compressor_train_last_part.find_fixed_shaft_speed(
            streams=streams_last_part,
            boundary_conditions=boundary_conditions_last_part,
            lower_bound_for_speed=self.minimum_speed,
            upper_bound_for_speed=self.maximum_speed,
        )

        if math.isclose(compressor_train_last_part.shaft.get_speed(), self.minimum_speed, rel_tol=EPSILON):
            compressor_train_results_last_part_with_optimal_speed_result = (
                compressor_train_last_part.evaluate_with_pressure_control(
                    streams=streams_last_part,
                    boundary_conditions=boundary_conditions_last_part,
                )
            )
        else:
            compressor_train_results_last_part_with_optimal_speed_result = (
                compressor_train_last_part.calculate_compressor_train(
                    streams=streams_last_part,
                    boundary_conditions=boundary_conditions_last_part,
                )
            )

        """
        Determine which of the first and last part will govern the speed to use
        Then run the last part as a single speed train with the speed chosen
        Fixme: Need to deliver the result in a proper format below.
        """
        if compressor_train_first_part.shaft.get_speed() > compressor_train_last_part.shaft.get_speed():
            compressor_train_last_part.shaft.set_speed(compressor_train_first_part.shaft.get_speed())
            compressor_train_results_last_part_with_pressure_control = (
                compressor_train_last_part.evaluate_with_pressure_control(
                    streams=streams_last_part,
                    boundary_conditions=boundary_conditions_last_part,
                )
            )
            compressor_train_results_to_return_first_part = (
                compressor_train_results_first_part_with_optimal_speed_result
            )
            compressor_train_results_to_return_last_part = compressor_train_results_last_part_with_pressure_control

        else:
            compressor_train_first_part.shaft.set_speed(compressor_train_last_part.shaft.get_speed())
            compressor_train_results_first_part_with_pressure_control = (
                compressor_train_first_part.evaluate_with_pressure_control(
                    streams=streams_first_part,
                    boundary_conditions=boundary_conditions_first_part,
                )
            )
            compressor_train_results_to_return_first_part = compressor_train_results_first_part_with_pressure_control
            compressor_train_results_to_return_last_part = compressor_train_results_last_part_with_optimal_speed_result

        compressor_train_results_to_return_stage_results = list(
            compressor_train_results_to_return_first_part.stage_results
            + compressor_train_results_to_return_last_part.stage_results
        )

        train_result = CompressorTrainResultSingleTimeStep(
            inlet_stream=compressor_train_results_to_return_first_part.inlet_stream,
            outlet_stream=compressor_train_results_to_return_last_part.outlet_stream,
            speed=compressor_train_first_part.shaft.get_speed(),
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
            boundary_conditions=boundary_conditions,
            results=train_result,
        )

        train_result.target_pressure_status = target_pressure_status

        return train_result


def split_streams_on_stage_number(
    compressor_train: CompressorTrainCommonShaftMultipleStreamsAndPressures,
    streams: list[FluidStream | float],
    stage_number: int,
) -> tuple[list[FluidStream | float], list[FluidStream | float]]:
    """
    Splits the stream rates for a compressor train into two lists at the specified stage number.

    The first list contains rates for streams connected to stages before the split.
    The second list contains the rate at the split stage and rates for streams connected to stages at or after the split.

    Args:
        compressor_train: The compressor train instance containing stream and stage information.
        streams: The streams being processed.
        stage_number: The stage index at which to split the rates (0-based).

    Returns:
        Tuple containing:
            - List of rates for the first part (before the split stage).
            - List of rates for the last part (from the split stage onward).
    """
    streams_first_part = [
        streams[i] for i, stream in enumerate(compressor_train.streams) if stream.connected_to_stage_no < stage_number
    ]

    streams_last_part = [
        streams[i] for i, stream in enumerate(compressor_train.streams) if stream.connected_to_stage_no >= stage_number
    ]
    streams_last_part.insert(
        0, streams_first_part[0]
    )  # just a placeholder for the stream coming out of first part after calculation

    return streams_first_part, streams_last_part


def split_train_on_stage_number(
    compressor_train: CompressorTrainCommonShaftMultipleStreamsAndPressures,
    stage_number: int,
    pressure_control_first_part: FixedSpeedPressureControl | None = None,
    pressure_control_last_part: FixedSpeedPressureControl | None = None,
) -> tuple[
    CompressorTrainCommonShaftMultipleStreamsAndPressures,
    CompressorTrainCommonShaftMultipleStreamsAndPressures,
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

    # Create streams for first part
    streams_first_part = [stream for stream in compressor_train.streams if stream.connected_to_stage_no < stage_number]
    assert isinstance(compressor_train._fluid_factory, list)  # for mypy
    fluid_factory_first_part = [
        fluid_factory
        for stream, fluid_factory in zip(compressor_train.streams, compressor_train._fluid_factory)
        if stream.connected_to_stage_no < stage_number
    ]

    compressor_train_first_part = CompressorTrainCommonShaftMultipleStreamsAndPressures(
        streams=streams_first_part,
        shaft=VariableSpeedShaft(),
        energy_usage_adjustment_constant=compressor_train.energy_usage_adjustment_constant,
        energy_usage_adjustment_factor=compressor_train.energy_usage_adjustment_factor,
        stages=compressor_train.stages[:stage_number],
        calculate_max_rate=compressor_train.calculate_max_rate
        if compressor_train.calculate_max_rate is not None
        else False,
        maximum_power=compressor_train.maximum_power,
        pressure_control=pressure_control_first_part,
        stage_number_interstage_pressure=compressor_train.stage_number_interstage_pressure,
    )

    compressor_train_first_part._fluid_factory = fluid_factory_first_part

    # Create streams for last part
    streams_last_part = [
        deepcopy(compressor_train.streams[compressor_train.inlet_stream_connected_to_stage.get(0)[0]])  # type: ignore[index]
    ]  # placeholder for stream coming out of first train, updated at runtime
    streams_last_part.extend(
        [
            FluidStreamObjectForMultipleStreams(
                fluid_model=stream.fluid_model,
                is_inlet_stream=stream.is_inlet_stream,
                connected_to_stage_no=stream.connected_to_stage_no - stage_number,
            )
            for stream in compressor_train.streams
            if stream.connected_to_stage_no >= stage_number
        ]
    )
    # Last part initially uses the main fluid factory (placeholder)
    # This will be updated at runtime after the fluid model (composition) is changed

    fluid_factory_last_part = [deepcopy(compressor_train._fluid_factory[0])]
    fluid_factory_last_part.extend(
        [
            fluid_factory
            for stream, fluid_factory in zip(compressor_train.streams, compressor_train._fluid_factory)
            if stream.connected_to_stage_no >= stage_number
        ]
    )

    compressor_train_last_part = CompressorTrainCommonShaftMultipleStreamsAndPressures(
        streams=streams_last_part,
        energy_usage_adjustment_constant=compressor_train.energy_usage_adjustment_constant,
        energy_usage_adjustment_factor=compressor_train.energy_usage_adjustment_factor,
        stages=compressor_train.stages[stage_number:],
        shaft=VariableSpeedShaft(),
        calculate_max_rate=compressor_train.calculate_max_rate
        if compressor_train.calculate_max_rate is not None
        else False,
        maximum_power=compressor_train.maximum_power,
        pressure_control=pressure_control_last_part,
        stage_number_interstage_pressure=compressor_train.stage_number_interstage_pressure,
    )
    compressor_train_last_part._fluid_factory = fluid_factory_last_part

    return compressor_train_first_part, compressor_train_last_part
