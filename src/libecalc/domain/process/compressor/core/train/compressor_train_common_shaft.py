import math
from copy import deepcopy
from functools import partial
from typing import Self

from libecalc.common.errors.exceptions import IllegalStateException
from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl
from libecalc.common.logger import logger
from libecalc.domain.component_validation_error import (
    ProcessChartTypeValidationException,
    ProcessDischargePressureValidationException,
)
from libecalc.domain.process.compressor.core.results import (
    CompressorTrainResultSingleTimeStep,
)
from libecalc.domain.process.compressor.core.train.base import CompressorTrainModel
from libecalc.domain.process.compressor.core.train.stage import CompressorTrainStage
from libecalc.domain.process.compressor.core.train.train_evaluation_input import CompressorTrainEvaluationInput
from libecalc.domain.process.compressor.core.train.utils.common import (
    EPSILON,
    POWER_CALCULATION_TOLERANCE,
    PRESSURE_CALCULATION_TOLERANCE,
    RATE_CALCULATION_TOLERANCE,
)
from libecalc.domain.process.compressor.core.train.utils.numeric_methods import (
    find_root,
    maximize_x_given_boolean_condition_function,
)
from libecalc.domain.process.core.results.compressor import TargetPressureStatus
from libecalc.domain.process.entities.shaft import Shaft, SingleSpeedShaft, VariableSpeedShaft
from libecalc.domain.process.value_objects.chart.chart_area_flag import ChartAreaFlag
from libecalc.domain.process.value_objects.fluid_stream import FluidService
from libecalc.domain.process.value_objects.fluid_stream.fluid_model import FluidModel


class CompressorTrainCommonShaft(CompressorTrainModel):
    """A model of a compressor train with one or multiple compressor stages on a common shaft.

    In general, a compressor train (series of compressors) is running on a single shaft, meaning each stage will always
    have the same speed. Given inlet fluid conditions (composition, temperature, pressure, rate) and a shaft speed, the
    intermediate pressures (and temperature before cooling) between stages and the outlet pressure (and temperature) is
    given.

    Args:
        fluid_service (FluidService interface): Singleton service for fluid thermodynamic operations.
        energy_usage_adjustment_constant (float): Constant to be added to the computed power. Defaults to 0.0.
        energy_usage_adjustment_factor (float): Factor to be multiplied to computed power. Defaults to 1.0.
        stages (list[CompressorTrainStage]): List of compressor stages in the train.
        shaft (Shaft): The shaft the compressor stages are mounted on.
        pressure_control (FixedSpeedPressureControl | None, optional): If set, the compressor train will
            operate with pressure control. Meaning that if the target discharge pressure is not reached at the given
            speed, the compressor train will operate at the maximum possible discharge pressure at the given speed.
            Defaults to None.
        calculate_max_rate (bool, optional): Whether to calculate the maximum rate the compressor train can
            operate at for the given inlet and outlet pressure. Defaults to False.
        maximum_power (float | None, optional): Maximum power [MW] the compressor train can use. If the
            calculated power exceeds this value, the result will be flagged as above maximum power. If None,
            no maximum power limit is applied. Defaults to None.

    To solve this for a given outlet pressure, one must iterate to find the speed.

    Compressor charts:
    The compressor charts must be pre-defined with a list of one or more compressor curves - each connected to a single
    speed.

    """

    def __init__(
        self,
        energy_usage_adjustment_constant: float,
        energy_usage_adjustment_factor: float,
        stages: list[CompressorTrainStage],
        fluid_service: FluidService,
        shaft: Shaft,
        pressure_control: FixedSpeedPressureControl | None = None,
        calculate_max_rate: bool = False,
        maximum_power: float | None = None,
        maximum_discharge_pressure: float | None = None,
        stage_number_interstage_pressure: int | None = None,
    ):
        logger.debug(f"Creating CompressorTrainCommonShaft with n_stages: {len(stages)}")
        self.shaft = shaft
        super().__init__(
            energy_usage_adjustment_constant=energy_usage_adjustment_constant,
            energy_usage_adjustment_factor=energy_usage_adjustment_factor,
            stages=stages,
            fluid_service=fluid_service,
            maximum_power=maximum_power,
            pressure_control=pressure_control,
            calculate_max_rate=calculate_max_rate,
            maximum_discharge_pressure=maximum_discharge_pressure,
            stage_number_interstage_pressure=stage_number_interstage_pressure,
        )

        self._validate_maximum_discharge_pressure()
        self._validate_stages(stages)
        self._validate_shaft()

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

    @property
    def is_variable_speed(self):
        return all(stage.compressor.compressor_chart.is_variable_speed for stage in self.stages)

    def _validate_positive_ingoing_rates(self, constraints: CompressorTrainEvaluationInput) -> bool:
        if not constraints.rates or not any(
            rate > 0 for rate, port in zip(constraints.rates, self.ports) if port.is_inlet_port
        ):
            return False
        return True

    def _validate_nonnegative_stage_rates(self, constraints: CompressorTrainEvaluationInput):
        if not constraints.rates:
            raise ValueError("Rates must be provided for validation.")
        for stage_number in range(len(self.stages)):
            net_rate = sum(
                constraints.rates[i] if port.is_inlet_port else -constraints.rates[i]
                for i, port in enumerate(self.ports)
                if port.connected_to_stage_no <= stage_number
            )
            if net_rate < 0:
                raise ValueError(
                    f"Net rate at stage {stage_number} is negative: {net_rate}. "
                    "Sum of ingoing and outgoing rates at each stage must be >= 0."
                )

    def evaluate_given_constraints(
        self,
        constraints: CompressorTrainEvaluationInput,
        fixed_speed: float | None = None,
    ) -> CompressorTrainResultSingleTimeStep:
        self.reset_rate_modifiers()
        self._validate_nonnegative_stage_rates(constraints)
        if self._validate_positive_ingoing_rates(constraints):
            if constraints.interstage_pressure is not None:
                if fixed_speed is not None:
                    raise ValueError("You can not set a fixed speed when also setting an interstage pressure.")
                self._check_intermediate_pressure_stage_number_is_valid(
                    _stage_number_intermediate_pressure=self.stage_number_interstage_pressure,
                    number_of_stages=len(self.stages),
                )
                return self.find_and_calculate_for_compressor_train_with_two_pressure_requirements(
                    stage_number_for_intermediate_pressure_target=self.stage_number_interstage_pressure,
                    constraints=constraints,
                    pressure_control_first_part=self.pressure_control_first_part,
                    pressure_control_last_part=self.pressure_control_last_part,
                )
            if fixed_speed is None:
                self.find_fixed_shaft_speed_given_constraints(constraints=constraints)
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
                train_result = self.evaluate_with_pressure_control_given_constraints(constraints=constraints)
            return train_result
        else:
            return CompressorTrainResultSingleTimeStep.create_empty(number_of_stages=len(self.stages))

    def calculate_compressor_train(
        self,
        constraints: CompressorTrainEvaluationInput,
    ) -> CompressorTrainResultSingleTimeStep:
        """
        Simulate the compressor train for the given inlet conditions, stream rates, and shaft speed.

        This method models the flow through each stage of the compressor train, accounting for multiple inlet and outlet
        streams, anti-surge valve recirculation, and possible subtrain configurations. It computes the resulting outlet
        stream, per-stage results (including conditions and power), and overall train performance.

        Typical usage scenarios:
            1. Standard train: ports[0] is the main inlet.
            2. First subtrain (with intermediate pressure target): self.ports[0] is the inlet.
            3. Last subtrain (after a split): self.ports[0] may be an entering or leaving stream, and the inlet fluid
               is set from the first subtrain.

        Args:
            constraints (CompressorTrainEvaluationInput): The constraints for the evaluation.

        Returns:
            CompressorTrainResultSingleTimeStep: Object containing inlet/outlet streams, per-stage results, speed,
            total power, and pressure status.
        """
        # This multiple streams train also requires rates to be set
        assert constraints.rates is not None
        assert constraints.suction_pressure is not None
        assert isinstance(self._fluid_model, list)

        fluid_streams = []
        for i, port in enumerate(self.ports):
            if port.is_inlet_port:
                stream_fluid_model = self._fluid_model[i]
                if stream_fluid_model is not None:
                    fluid_streams.append(
                        self._fluid_service.create_stream_from_standard_rate(
                            fluid_model=stream_fluid_model,
                            pressure_bara=constraints.suction_pressure,
                            temperature_kelvin=self.stages[0].inlet_temperature_kelvin,
                            standard_rate_m3_per_day=constraints.rates[i],
                        )
                    )

        previous_stage_outlet_stream = train_inlet_stream = fluid_streams[0]
        inlet_stream_counter = 1
        stage_results = []

        for stage_number, stage in enumerate(self.stages):
            stage_inlet_stream = previous_stage_outlet_stream

            rates_out_of_splitter = [
                constraints.rates[stream_number]
                for stream_number in self.outlet_port_connected_to_stage.get(stage_number, [])
            ]
            streams_in_to_mixer = []
            for stream_number in self.inlet_port_connected_to_stage.get(stage_number, []):
                if stream_number > 0:
                    if inlet_stream_counter < len(fluid_streams):
                        # Create fluid at stage inlet conditions using fluid service
                        new_fluid = stage.fluid_service.create_fluid(
                            fluid_streams[inlet_stream_counter].fluid_model,
                            stage_inlet_stream.pressure_bara,
                            stage_inlet_stream.temperature_kelvin,
                        )
                        streams_in_to_mixer.append(fluid_streams[inlet_stream_counter].with_new_fluid(new_fluid))
                        inlet_stream_counter += 1

            stage_results.append(
                stage.evaluate(
                    inlet_stream_stage=stage_inlet_stream,
                    rates_out_of_splitter=rates_out_of_splitter,
                    streams_in_to_mixer=streams_in_to_mixer,
                )
            )

            previous_stage_outlet_stream = stage_results[-1].outlet_stream

        # check if target pressures are met
        target_pressure_status = self.check_target_pressures(constraints=constraints, results=stage_results)

        return CompressorTrainResultSingleTimeStep(
            inlet_stream=train_inlet_stream,
            outlet_stream=previous_stage_outlet_stream,
            stage_results=stage_results,
            speed=self.shaft.get_speed(),
            above_maximum_power=(
                sum(stage_result.power_megawatt for stage_result in stage_results) > self.maximum_power
                if self.maximum_power
                else False
            ),
            target_pressure_status=target_pressure_status,
        )

    def _validate_stages(self, stages: list[CompressorTrainStage]):
        # Check that the compressor stages have overlapping speed ranges
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

    def _get_max_std_rate_single_timestep(
        self,
        constraints: CompressorTrainEvaluationInput,
        allow_asv: bool = False,
    ) -> float:
        """Calculate the max standard rate [Sm3/day] that the compressor train can operate at for a single time step.

        The maximum rate can be found in 3 areas:
            1. The compressor train can't reach the required target pressure regardless of speed -> Left of the chart.
            2. The compressor train hits the required outlet pressure on the maximum speed curve -> On the max speed curve.
            3. The compressor train hits the required outlet pressure somewhere on the stone wall -> On the stone wall.

        This is how we search for the solution:
            1. If the compressor train cannot reach the target pressure regardless of rate and ASV (if allowed). Return 0.
            2. Else if the solution is along the maximum speed curve;
                then we iterate on mass rate along the maximum speed curve to find a solution.
            3. Else if the pressure is too high and pressure control is choking either upstream or downstream,
                then the solution is still on the max speed curve.
            4. Else if the solution is on the "stone wall";
                then we iterate on speed along the "stone wall" to find a solution.
            5. Else if the outlet pressure is still too high is still too low, the pressure points given are not valid.
                We still want to provide a maximum rate number as we do not want the consumer system calculations to fail,
                but rather trigger an infeasible solution at evaluation. Thus - return minimum rate for maximum speed for
                pressure ratios too high, and minimum rate for stone wall (i.e. maximum rate for minimum speed) for pressure
                ratios too low.

        Note: we only have information enough to make the inlet streams. For the outlet streams, we only have
        pressure, the temperature needs to be calculated as part of the process

        Note: We use this method's variable scope within the inner functions.

        Note: In the future:
            We have density_per_stage, that can be used to calculate the inlet actual rate for any stage.
            May be useful to add mass_rate_kg_per_hour to StageResultSingleCalculationPoint.

        Args:
            constraints (CompressorTrainEvaluationInput): The constraints for the evaluation.
            allow_asv: Whether to allow anti-surge valve recirculation when calculating maximum rate.

        Returns:
            Standard volume rate [Sm3/day]

        """
        assert constraints.suction_pressure is not None, "suction_pressure is required for maximum rate calculation"
        fluid_model = self.fluid_model
        inlet_density = self._fluid_service.create_fluid(
            fluid_model=fluid_model,
            pressure_bara=constraints.suction_pressure,
            temperature_kelvin=self.stages[0].inlet_temperature_kelvin,
        ).density

        def _calculate_train_result(mass_rate: float, speed: float) -> CompressorTrainResultSingleTimeStep:
            """Partial function of self.calculate_compressor_train_given_speed
            where we only pass mass_rate.
            """
            self.shaft.set_speed(speed)
            return self.calculate_compressor_train(
                constraints=constraints.create_conditions_with_new_input(
                    new_rate=self._fluid_service.mass_rate_to_standard_rate(fluid_model, mass_rate),
                )
            )

        def _calculate_train_result_given_ps_pd(mass_rate: float) -> CompressorTrainResultSingleTimeStep:
            """Partial function of self.evaluate_given_constraints
            where we only pass mass_rate.
            """
            return self.evaluate_given_constraints(
                constraints=constraints.create_conditions_with_new_input(
                    new_rate=self._fluid_service.mass_rate_to_standard_rate(fluid_model, mass_rate),
                )
            )

        def _calculate_train_result_given_speed_at_stone_wall(
            speed: float,
        ) -> CompressorTrainResultSingleTimeStep:
            """Partial function of self.calculate_compressor_train.
            Same as above, but mass rate is pinned to the "stone wall" as a function of speed.
            """
            _max_valid_mass_rate_at_given_speed = maximize_x_given_boolean_condition_function(
                x_min=self.stages[0].compressor.compressor_chart.minimum_rate_as_function_of_speed(speed)
                * inlet_density,
                x_max=self.stages[0].compressor.compressor_chart.maximum_rate_as_function_of_speed(speed)
                * inlet_density,
                bool_func=lambda x: _calculate_train_result(mass_rate=x, speed=speed).within_capacity,
                convergence_tolerance=1e-3,
                maximum_number_of_iterations=20,
            )

            return self.calculate_compressor_train(
                constraints=constraints.create_conditions_with_new_input(
                    new_rate=self._fluid_service.mass_rate_to_standard_rate(
                        fluid_model, _max_valid_mass_rate_at_given_speed
                    ),
                )
            )

        # Same as the partial functions above, but simpler syntax using partial()
        _calculate_train_result_at_max_speed_given_mass_rate = partial(
            _calculate_train_result, speed=self.maximum_speed
        )

        _calculate_train_result_at_min_speed_given_mass_rate = partial(
            _calculate_train_result, speed=self.minimum_speed
        )

        # Using first stage as absolute (initial) bounds on min and max rate at max speed. Checking validity later.
        min_mass_rate_at_max_speed_first_stage = (
            self.stages[0].compressor.compressor_chart.maximum_speed_curve.minimum_rate * inlet_density
        )
        max_mass_rate_at_max_speed_first_stage = (
            self.stages[0].compressor.compressor_chart.maximum_speed_curve.maximum_rate * inlet_density
        )
        max_mass_rate_at_min_speed_first_stage = (
            self.stages[0].compressor.compressor_chart.maximum_rate_as_function_of_speed(
                self.stages[0].compressor.compressor_chart.minimum_speed
            )
            * inlet_density
        )

        result_min_mass_rate_at_max_speed_first_stage = _calculate_train_result_at_max_speed_given_mass_rate(
            mass_rate=min_mass_rate_at_max_speed_first_stage
        )
        result_max_mass_rate_at_max_speed_first_stage = _calculate_train_result_at_max_speed_given_mass_rate(
            mass_rate=max_mass_rate_at_max_speed_first_stage
        )
        result_max_mass_rate_at_min_speed_first_stage = _calculate_train_result_at_min_speed_given_mass_rate(
            mass_rate=max_mass_rate_at_min_speed_first_stage
        )

        # Ensure that the minimum mass rate at max speed is valid for the whole train.
        if not result_min_mass_rate_at_max_speed_first_stage.within_capacity:
            if allow_asv:
                min_mass_rate_at_max_speed = EPSILON
                result_min_mass_rate_at_max_speed = _calculate_train_result_at_max_speed_given_mass_rate(
                    mass_rate=min_mass_rate_at_max_speed
                )
                if not result_min_mass_rate_at_max_speed.within_capacity:
                    logger.debug(
                        "There are no valid mass rate for VariableSpeedCompressorTrain."
                        "Infeasible solution. Returning max rate 0.0 (None)."
                    )
                    return 0.0
                max_mass_rate_at_max_speed = maximize_x_given_boolean_condition_function(
                    x_min=EPSILON,
                    x_max=min_mass_rate_at_max_speed_first_stage,
                    bool_func=lambda x: _calculate_train_result_at_max_speed_given_mass_rate(
                        mass_rate=x
                    ).within_capacity,
                    convergence_tolerance=1e-3,
                    maximum_number_of_iterations=20,
                )
                result_max_mass_rate_at_max_speed = _calculate_train_result_at_max_speed_given_mass_rate(
                    mass_rate=max_mass_rate_at_max_speed
                )
            else:
                logger.debug(
                    "There are no valid common mass rate for VariableSpeedCompressorTrain, and ASV is not allowed."
                    "Infeasible solution. Returning max rate 0.0 (None)."
                )
                return 0.0
        else:
            min_mass_rate_at_max_speed = min_mass_rate_at_max_speed_first_stage
            result_min_mass_rate_at_max_speed = result_min_mass_rate_at_max_speed_first_stage

            # Ensuring that the maximum mass rate at max speed is valid for the whole train.
            if not result_max_mass_rate_at_max_speed_first_stage.within_capacity:
                max_mass_rate_at_max_speed = maximize_x_given_boolean_condition_function(
                    x_min=min_mass_rate_at_max_speed,
                    x_max=max_mass_rate_at_max_speed_first_stage,
                    bool_func=lambda x: _calculate_train_result_at_max_speed_given_mass_rate(
                        mass_rate=x
                    ).within_capacity,
                    convergence_tolerance=1e-3,
                    maximum_number_of_iterations=20,
                )
                result_max_mass_rate_at_max_speed = _calculate_train_result_at_max_speed_given_mass_rate(
                    mass_rate=max_mass_rate_at_max_speed
                )
            else:
                max_mass_rate_at_max_speed = max_mass_rate_at_max_speed_first_stage
                result_max_mass_rate_at_max_speed = result_max_mass_rate_at_max_speed_first_stage

        # Solution scenario 1. Infeasible. Target pressure is too high.
        if (
            constraints.discharge_pressure is not None
            and result_min_mass_rate_at_max_speed.discharge_pressure < constraints.discharge_pressure
        ):
            return 0.0

        # Solution scenario 2. Solution is at maximum speed curve.
        elif (
            constraints.discharge_pressure is not None
            and constraints.discharge_pressure >= result_max_mass_rate_at_max_speed.discharge_pressure
        ):
            """
            Iterating along max speed curve for first stage.
            """
            target_discharge_pressure = constraints.discharge_pressure
            result_mass_rate = find_root(
                lower_bound=min_mass_rate_at_max_speed,
                upper_bound=max_mass_rate_at_max_speed,
                func=lambda x: _calculate_train_result_at_max_speed_given_mass_rate(mass_rate=x).discharge_pressure
                - target_discharge_pressure,
                relative_convergence_tolerance=1e-3,
                maximum_number_of_iterations=20,
            )
            rate_to_return = result_mass_rate * (1 - RATE_CALCULATION_TOLERANCE)

        # Solution 3: If solution not found along max speed curve, and pressure control is downstream choke, we should
        # run at max_mass_rate, but using the defined pressure control.
        elif self.pressure_control == FixedSpeedPressureControl.DOWNSTREAM_CHOKE:
            rate_to_return = max_mass_rate_at_max_speed * (1 - RATE_CALCULATION_TOLERANCE)

        # if pressure control is upstream choke, we find the new maximum rate with the reduced inlet pressure
        elif self.pressure_control == FixedSpeedPressureControl.UPSTREAM_CHOKE:
            rate_to_return = maximize_x_given_boolean_condition_function(
                x_min=0,
                x_max=max_mass_rate_at_max_speed_first_stage,
                bool_func=lambda x: _calculate_train_result_given_ps_pd(mass_rate=x).within_capacity,
                convergence_tolerance=1e-3,
                maximum_number_of_iterations=20,
            )

        # Solution scenario 4. Solution at the "Stone wall".
        else:
            # Ensuring that the maximum mass rate at min speed is valid for the whole train.
            if not result_max_mass_rate_at_min_speed_first_stage.within_capacity:
                max_mass_rate_at_min_speed = maximize_x_given_boolean_condition_function(
                    x_min=EPSILON,
                    x_max=max_mass_rate_at_min_speed_first_stage,
                    bool_func=lambda x: _calculate_train_result_at_min_speed_given_mass_rate(
                        mass_rate=x
                    ).within_capacity,
                )
                result_max_mass_rate_at_min_speed = _calculate_train_result_at_min_speed_given_mass_rate(
                    mass_rate=max_mass_rate_at_min_speed
                )
            else:
                # max_mass_rate_at_min_speed = max_mass_rate_at_max_speed_first_stage
                result_max_mass_rate_at_min_speed = result_max_mass_rate_at_min_speed_first_stage

            if (
                constraints.discharge_pressure is not None
                and result_max_mass_rate_at_max_speed.discharge_pressure
                >= constraints.discharge_pressure
                >= result_max_mass_rate_at_min_speed.discharge_pressure
            ):
                # iterate along stone wall until target discharge pressure is reached
                target_discharge_pressure = constraints.discharge_pressure
                result_speed = find_root(
                    lower_bound=self.minimum_speed,
                    upper_bound=self.maximum_speed,
                    func=lambda x: _calculate_train_result_given_speed_at_stone_wall(speed=x).discharge_pressure
                    - target_discharge_pressure,
                )
                self.shaft.set_speed(result_speed)
                compressor_train_result = _calculate_train_result_given_speed_at_stone_wall(speed=result_speed)

                rate_to_return = compressor_train_result.mass_rate_kg_per_hour * (1 - RATE_CALCULATION_TOLERANCE)

            # Solution scenario 5. Too high pressure even at min speed and max flow rate.
            elif (
                constraints.discharge_pressure is not None
                and result_max_mass_rate_at_min_speed.discharge_pressure > constraints.discharge_pressure
            ):
                return 0.0
            else:
                msg = "You should not end up here. Please contact eCalc support."
                logger.exception(msg)
                raise IllegalStateException(msg)

        # Check that rate_to_return, suction_pressure and discharge_pressure does not require too much power.
        # If so, reduce rate such that power comes below maximum power
        maximum_power = self.maximum_power
        if not maximum_power:
            result = self._fluid_service.mass_rate_to_standard_rate(fluid_model, rate_to_return)
            return float(result)
        elif (
            self.evaluate_given_constraints(
                constraints=constraints.create_conditions_with_new_input(
                    new_rate=self._fluid_service.mass_rate_to_standard_rate(fluid_model, rate_to_return),
                )
            ).power_megawatt
            > maximum_power
        ):
            # check if minimum_rate gives too high power consumption
            result_with_minimum_rate = self.evaluate_given_constraints(
                constraints=constraints.create_conditions_with_new_input(
                    new_rate=EPSILON,
                )
            )
            if result_with_minimum_rate.power_megawatt > maximum_power:
                return 0.0  # can't find solution
            else:
                # iterate between rate with minimum power, and the previously found rate to return, to find the
                # maximum rate that gives power consumption below maximum power

                result = self._fluid_service.mass_rate_to_standard_rate(
                    fluid_model,
                    find_root(
                        lower_bound=result_with_minimum_rate.stage_results[0].mass_rate_asv_corrected_kg_per_hour,
                        upper_bound=rate_to_return,
                        func=lambda x: self.evaluate_given_constraints(
                            constraints=constraints.create_conditions_with_new_input(
                                new_rate=self._fluid_service.mass_rate_to_standard_rate(fluid_model, x),
                            )
                        ).power_megawatt
                        - maximum_power * (1 - POWER_CALCULATION_TOLERANCE),
                        relative_convergence_tolerance=1e-3,
                        maximum_number_of_iterations=20,
                    ),
                )
                return float(result)
        else:
            # maximum power defined, but found rate is below maximum power
            result = self._fluid_service.mass_rate_to_standard_rate(fluid_model, rate_to_return)
            return float(result)

    def _validate_maximum_discharge_pressure(self):
        if self.maximum_discharge_pressure is not None and self.maximum_discharge_pressure < 0:
            msg = f"maximum_discharge_pressure must be greater than or equal to 0. Invalid value: {self.maximum_discharge_pressure}"

            raise ProcessDischargePressureValidationException(message=str(msg))

    def _validate_shaft(self):
        if not isinstance(self.shaft, Shaft):
            raise ValueError("A common shaft compressor train must have a shaft defined")
        if self.is_variable_speed and isinstance(self.shaft, SingleSpeedShaft):
            raise ValueError(
                "A common shaft compressor train with multiple speeds must have a variable speed shaft defined."
            )
        elif not self.is_variable_speed:
            if isinstance(self.shaft, VariableSpeedShaft):
                raise ValueError(
                    "A common shaft compressor train with a single speed must have a single speed shaft defined."
                )
            self.shaft.set_speed(self.minimum_speed)

    def evaluate_with_pressure_control_given_constraints(
        self, constraints: CompressorTrainEvaluationInput
    ) -> CompressorTrainResultSingleTimeStep:
        """

        Args:
            constraints:

        Returns:
            CompressorTrainResultSingleTimeStep: The result of the compressor train evaluation.
        """
        if not self.shaft.speed_is_defined:
            raise ValueError(
                "Pressure control can only be applied after a speed curve is selected / the speed is fixed."
            )
        if self.pressure_control == FixedSpeedPressureControl.DOWNSTREAM_CHOKE:
            train_result = self._evaluate_train_with_downstream_choking(
                constraints=constraints,
            )
        elif self.pressure_control == FixedSpeedPressureControl.UPSTREAM_CHOKE:
            train_result = self._evaluate_train_with_upstream_choking(
                constraints=constraints,
            )
        elif self.pressure_control == FixedSpeedPressureControl.INDIVIDUAL_ASV_RATE:
            train_result = self._evaluate_train_with_individual_asv_rate(
                constraints=constraints,
            )
        elif self.pressure_control == FixedSpeedPressureControl.INDIVIDUAL_ASV_PRESSURE:
            train_result = self._evaluate_train_with_individual_asv_pressure(
                constraints=constraints,
            )
        elif self.pressure_control == FixedSpeedPressureControl.COMMON_ASV:
            train_result = self._evaluate_train_with_common_asv(
                constraints=constraints,
            )
        else:
            raise ValueError(f"Pressure control {self.pressure_control} not supported")

        return train_result

    def _evaluate_train_with_downstream_choking(
        self,
        constraints: CompressorTrainEvaluationInput,
    ) -> CompressorTrainResultSingleTimeStep:
        """
        Evaluate a single-speed compressor train's total power given mass rate, suction pressure, and discharge pressure.

        This method assumes that the discharge pressure is controlled to meet the target using a downstream choke valve.

        Args:
            constraints (CompressorTrainEvaluationInput): The constraints for the evaluation.

        Returns:
            CompressorTrainResultSingleTimeStep: The result of the evaluation for a single time step.
        """
        train_result = self.calculate_compressor_train(
            constraints=constraints,
        )

        if self.maximum_discharge_pressure is not None:
            if train_result.discharge_pressure * (1 + PRESSURE_CALCULATION_TOLERANCE) > self.maximum_discharge_pressure:
                new_train_result = self._evaluate_train_with_upstream_choking(
                    constraints=constraints.create_conditions_with_new_input(
                        new_discharge_pressure=self.maximum_discharge_pressure,
                    ),
                )
                train_result.stage_results = new_train_result.stage_results
                train_result.outlet_stream = new_train_result.outlet_stream
                train_result.target_pressure_status = self.check_target_pressures(
                    constraints=constraints,
                    results=train_result,
                )

        if train_result.target_pressure_status == TargetPressureStatus.ABOVE_TARGET_DISCHARGE_PRESSURE:
            # At this point, discharge_pressure must be set since we're checking target pressures
            assert constraints.discharge_pressure is not None
            new_fluid = self.stages[-1].fluid_service.create_fluid(
                train_result.outlet_stream.fluid_model,
                constraints.discharge_pressure,
                train_result.outlet_stream.temperature_kelvin,
            )
            train_result.outlet_stream = train_result.outlet_stream.with_new_fluid(new_fluid)
            train_result.target_pressure_status = self.check_target_pressures(
                constraints=constraints,
                results=train_result,
            )

        return train_result

    def _evaluate_train_with_upstream_choking(
        self,
        constraints: CompressorTrainEvaluationInput,
    ) -> CompressorTrainResultSingleTimeStep:
        """
        Evaluate the compressor train's total power assuming upstream choking is used to control suction pressure.

        This method iteratively adjusts the suction pressure to achieve the target discharge pressure.

        Args:
            constraints (CompressorTrainEvaluationInput): The constraints for the evaluation.

        Returns:
            CompressorTrainResultSingleTimeStep: The result of the evaluation for a single time step.
        """
        assert constraints.inlet_rate is not None
        assert constraints.suction_pressure is not None

        train_inlet_stream = self.train_inlet_stream(
            pressure=constraints.suction_pressure,
            temperature=self.stages[0].inlet_temperature_kelvin,
            rate=constraints.inlet_rate,
        )

        def _calculate_train_result_given_inlet_pressure(
            inlet_pressure: float,
        ) -> CompressorTrainResultSingleTimeStep:
            """Note that we use outside variables for clarity and to avoid class instances."""
            return self.calculate_compressor_train(
                constraints=constraints.create_conditions_with_new_input(
                    new_suction_pressure=inlet_pressure,
                ),
            )

        # This method requires discharge_pressure to be set
        assert constraints.discharge_pressure is not None
        target_discharge_pressure = constraints.discharge_pressure

        result_inlet_pressure = find_root(
            lower_bound=EPSILON + self.stages[0].pressure_drop_ahead_of_stage,
            upper_bound=target_discharge_pressure,
            func=lambda x: _calculate_train_result_given_inlet_pressure(inlet_pressure=x).discharge_pressure
            - target_discharge_pressure,
        )

        train_result = _calculate_train_result_given_inlet_pressure(inlet_pressure=result_inlet_pressure)
        train_result.inlet_stream = train_inlet_stream

        train_result.target_pressure_status = self.check_target_pressures(
            constraints=constraints,
            results=train_result,
        )
        return train_result

    def _evaluate_train_with_individual_asv_rate(
        self,
        constraints: CompressorTrainEvaluationInput,
    ) -> CompressorTrainResultSingleTimeStep:
        """
        Evaluate the total power of a single-speed compressor train given suction pressure, discharge pressure,
        and a minimum mass rate.

        This method assumes that the discharge pressure is controlled to meet the target using anti-surge valves (ASVs).
        The ASVs increase the net rate until the head is reduced enough in each compressor stage to meet the target
        discharge pressure. For multiple compressor stages, the ASV recirculation is distributed proportionally across
        all stages, ensuring the same ASV fraction is applied to each stage.

        The ASV fraction that results in the target discharge pressure is found using a Newton iteration

        Args:
            constraints (CompressorTrainEvaluationInput): The constraints for the evaluation.

        Returns:
            CompressorTrainResultSingleTimeStep: The result of the evaluation for a single time step.
        """

        def _calculate_train_result_given_asv_rate_margin(
            asv_rate_fraction: float,
        ) -> CompressorTrainResultSingleTimeStep:
            """Note that we use outside variables for clarity and to avoid class instances."""
            for stage in self.stages:
                stage.rate_modifier.fraction_of_available_capacity_to_recirculate = asv_rate_fraction
            return self.calculate_compressor_train(
                constraints=constraints,
            )

        minimum_asv_fraction = 0.0
        maximum_asv_fraction = 1.0
        train_result_for_minimum_asv_rate_fraction = _calculate_train_result_given_asv_rate_margin(
            asv_rate_fraction=minimum_asv_fraction
        )
        if (train_result_for_minimum_asv_rate_fraction.chart_area_status == ChartAreaFlag.ABOVE_MAXIMUM_FLOW_RATE) or (
            constraints.discharge_pressure is not None
            and constraints.discharge_pressure > train_result_for_minimum_asv_rate_fraction.discharge_pressure
        ):
            return train_result_for_minimum_asv_rate_fraction
        train_result_for_maximum_asv_rate_fraction = _calculate_train_result_given_asv_rate_margin(
            asv_rate_fraction=maximum_asv_fraction
        )
        if (
            constraints.discharge_pressure is not None
            and constraints.discharge_pressure < train_result_for_maximum_asv_rate_fraction.discharge_pressure
        ):
            return train_result_for_maximum_asv_rate_fraction

        # This method requires discharge_pressure for the Newton iteration
        assert constraints.discharge_pressure is not None
        target_discharge_pressure = constraints.discharge_pressure

        result_asv_rate_margin = find_root(
            lower_bound=0.0,
            upper_bound=1.0,
            func=lambda x: _calculate_train_result_given_asv_rate_margin(asv_rate_fraction=x).discharge_pressure
            - target_discharge_pressure,
        )
        # This mass rate, is the mass rate to use as mass rate after asv for each stage,
        # thus the asv in each stage should be set to correspond to this mass rate
        return _calculate_train_result_given_asv_rate_margin(asv_rate_fraction=result_asv_rate_margin)

    def _evaluate_train_with_individual_asv_pressure(
        self,
        constraints: CompressorTrainEvaluationInput,
    ) -> CompressorTrainResultSingleTimeStep:
        """
        Evaluate the compressor train's total power using individual ASV pressure control.

        This method ensures that the pressure ratio (discharge pressure / suction pressure) is equal across all compressors
        in the train. ASVs are independently adjusted to achieve the required discharge pressure for each compressor.

        Args:
            constraints (CompressorTrainEvaluationInput): The constraints for the evaluation.

        Returns:
            CompressorTrainResultSingleTimeStep: The result of the evaluation for a single time step.
        """
        # This method requires both suction and discharge pressure to be set
        assert constraints.suction_pressure is not None
        assert constraints.discharge_pressure is not None
        assert constraints.inlet_rate is not None

        fluid_model = self.fluid_model
        inlet_stream_train = self._fluid_service.create_stream_from_standard_rate(
            fluid_model=fluid_model,
            pressure_bara=constraints.suction_pressure,
            temperature_kelvin=self.stages[0].inlet_temperature_kelvin,
            standard_rate_m3_per_day=constraints.inlet_rate,
        )
        pressure_ratio_per_stage = self.calculate_pressure_ratios_per_stage(
            suction_pressure=constraints.suction_pressure,
            discharge_pressure=constraints.discharge_pressure,
        )
        inlet_stream_stage = inlet_stream_train
        stage_results = []
        for stage in self.stages:
            outlet_pressure_for_stage = inlet_stream_stage.pressure_bara * pressure_ratio_per_stage
            stage_result = stage.evaluate_given_speed_and_target_discharge_pressure(
                target_discharge_pressure=outlet_pressure_for_stage,
                inlet_stream_stage=inlet_stream_stage,
            )
            inlet_stream_stage = stage_result.outlet_stream
            stage_results.append(stage_result)

        # check if target pressures are met
        target_pressure_status = self.check_target_pressures(
            constraints=constraints,
            results=stage_results,
        )
        return CompressorTrainResultSingleTimeStep(
            inlet_stream=inlet_stream_train,
            outlet_stream=stage_result.outlet_stream,
            speed=float("nan"),
            stage_results=stage_results,
            target_pressure_status=target_pressure_status,
        )

    def _evaluate_train_with_common_asv(
        self,
        constraints: CompressorTrainEvaluationInput,
    ) -> CompressorTrainResultSingleTimeStep:
        """
        Evaluate the total power of a single-speed compressor train given suction pressure, discharge pressure,
        and a constant mass rate.

        This method assumes that the discharge pressure is controlled to meet the target using anti-surge valves (ASVs).
        The ASVs increase the net rate until the head is reduced enough in each compressor stage to meet the target
        discharge pressure. For multiple compressor stages, the ASV recirculation is applied over the entire train,
        ensuring a constant mass rate across all stages.

        A Newton iteration is used to find the mass rate that results in the target discharge pressure.

        Args:
            constraints (CompressorTrainEvaluationInput): The constraints for the evaluation.

        Returns:
            CompressorTrainResultSingleTimeStep: The result of the evaluation for a single time step.
        """
        assert constraints.inlet_rate is not None, "inlet rate is required for ASV pressure control"
        assert constraints.suction_pressure is not None, "suction_pressure is required for ASV pressure control"

        fluid_model = self.fluid_model
        minimum_mass_rate_kg_per_hour = self._fluid_service.standard_rate_to_mass_rate(
            fluid_model=fluid_model,
            standard_rate_m3_per_day=constraints.inlet_rate,
        )
        # Iterate on rate until pressures are met
        density_train_inlet_fluid = self._fluid_service.create_fluid(
            fluid_model=fluid_model,
            pressure_bara=constraints.suction_pressure,
            temperature_kelvin=self.stages[0].inlet_temperature_kelvin,
        ).density

        def _calculate_train_result_given_mass_rate(
            mass_rate_kg_per_hour: float,
        ) -> CompressorTrainResultSingleTimeStep:
            self.reset_rate_modifiers()
            return self.calculate_compressor_train(
                constraints=constraints.create_conditions_with_new_input(
                    new_rate=self._fluid_service.mass_rate_to_standard_rate(fluid_model, mass_rate_kg_per_hour),
                ),
            )

        def _calculate_train_result_given_additional_mass_rate(
            additional_mass_rate_kg_per_hour: float,
        ) -> CompressorTrainResultSingleTimeStep:
            for stage in self.stages:
                stage.rate_modifier.mass_rate_to_recirculate = additional_mass_rate_kg_per_hour
            return self.calculate_compressor_train(
                constraints=constraints,
            )

        # outer bounds for minimum and maximum mass rate without individual recirculation on stages will be the
        # minimum and maximum mass rate for the first stage, adjusted for the volume entering the first stage
        minimum_mass_rate = max(
            minimum_mass_rate_kg_per_hour,
            self.stages[0].compressor.compressor_chart.minimum_rate * density_train_inlet_fluid,
        )
        # note: we subtract EPSILON to avoid floating point issues causing the maximum mass rate to exceed chart area maximum rate after round-trip conversion (mass rate -> standard rat -> mass rate)
        maximum_mass_rate = (
            self.stages[0].compressor.compressor_chart.maximum_rate * density_train_inlet_fluid * (1 - EPSILON)
        )

        # if the minimum_mass_rate_kg_per_hour(i.e. before increasing rate with recirculation to lower pressure)
        # is already larger than the maximum mass rate, there is no need for optimization - just add result
        # with minimum_mass_rate_kg_per_hour (which will fail with above maximum flow rate)
        if minimum_mass_rate_kg_per_hour > maximum_mass_rate:
            return _calculate_train_result_given_mass_rate(mass_rate_kg_per_hour=minimum_mass_rate_kg_per_hour)

        train_result_for_minimum_mass_rate = _calculate_train_result_given_mass_rate(
            mass_rate_kg_per_hour=float(minimum_mass_rate)
        )
        train_result_for_maximum_mass_rate = _calculate_train_result_given_mass_rate(
            mass_rate_kg_per_hour=float(maximum_mass_rate)
        )
        if train_result_for_minimum_mass_rate.mass_rate_asv_corrected_is_constant_for_stages:
            if not train_result_for_maximum_mass_rate.mass_rate_asv_corrected_is_constant_for_stages:
                # find the maximum additional_mass_rate that gives train_results.is_valid
                maximum_mass_rate = maximize_x_given_boolean_condition_function(
                    x_min=0.0,
                    x_max=maximum_mass_rate,
                    bool_func=lambda x: _calculate_train_result_given_mass_rate(
                        mass_rate_kg_per_hour=x
                    ).mass_rate_asv_corrected_is_constant_for_stages,
                    convergence_tolerance=1e-3,
                    maximum_number_of_iterations=20,
                )
                train_result_for_maximum_mass_rate = _calculate_train_result_given_mass_rate(
                    mass_rate_kg_per_hour=maximum_mass_rate
                )
        elif train_result_for_maximum_mass_rate.mass_rate_asv_corrected_is_constant_for_stages:
            # find the minimum additional_mass_rate that gives all points internal
            minimum_mass_rate = -maximize_x_given_boolean_condition_function(
                x_min=-maximum_mass_rate,
                x_max=-minimum_mass_rate,
                bool_func=lambda x: _calculate_train_result_given_mass_rate(
                    mass_rate_kg_per_hour=-x
                ).mass_rate_asv_corrected_is_constant_for_stages,
                convergence_tolerance=1e-3,
                maximum_number_of_iterations=20,
            )
            train_result_for_minimum_mass_rate = _calculate_train_result_given_mass_rate(
                mass_rate_kg_per_hour=minimum_mass_rate
            )
        else:
            # Try to find a point with all internal points. Testing 10 evenly spaced additional mass rates.
            # If none of those give a valid results, the compressor train is poorly designed...
            inc = 0.1
            train_result_for_mass_rate = _calculate_train_result_given_mass_rate(
                mass_rate_kg_per_hour=minimum_mass_rate + inc * (maximum_mass_rate - minimum_mass_rate)
            )
            while not train_result_for_mass_rate.mass_rate_asv_corrected_is_constant_for_stages:
                inc += 0.1
                if inc >= 1:
                    logger.error("Single speed train with Common ASV pressure control has no solution!")
                train_result_for_mass_rate = _calculate_train_result_given_mass_rate(
                    mass_rate_kg_per_hour=minimum_mass_rate + inc * (maximum_mass_rate - minimum_mass_rate)
                )

            # found one solution, now find min and max
            minimum_mass_rate = -maximize_x_given_boolean_condition_function(
                x_min=-(minimum_mass_rate + inc * (maximum_mass_rate - minimum_mass_rate)),
                x_max=-minimum_mass_rate,
                bool_func=lambda x: _calculate_train_result_given_mass_rate(
                    mass_rate_kg_per_hour=-x
                ).mass_rate_asv_corrected_is_constant_for_stages,
                convergence_tolerance=1e-3,
                maximum_number_of_iterations=20,
            )
            maximum_mass_rate = maximize_x_given_boolean_condition_function(
                x_min=(minimum_mass_rate + inc * (maximum_mass_rate - minimum_mass_rate)),
                x_max=maximum_mass_rate,
                bool_func=lambda x: _calculate_train_result_given_mass_rate(
                    mass_rate_kg_per_hour=x
                ).mass_rate_asv_corrected_is_constant_for_stages,
                convergence_tolerance=1e-3,
                maximum_number_of_iterations=20,
            )
            train_result_for_minimum_mass_rate = _calculate_train_result_given_mass_rate(
                mass_rate_kg_per_hour=minimum_mass_rate
            )
            train_result_for_maximum_mass_rate = _calculate_train_result_given_mass_rate(
                mass_rate_kg_per_hour=maximum_mass_rate
            )
        if (
            constraints.discharge_pressure is not None
            and constraints.discharge_pressure > train_result_for_minimum_mass_rate.discharge_pressure
        ):
            # will never reach target pressure, too high
            return train_result_for_minimum_mass_rate
        if (
            constraints.discharge_pressure is not None
            and constraints.discharge_pressure < train_result_for_maximum_mass_rate.discharge_pressure
        ):
            # will never reach target pressure, too low
            return train_result_for_maximum_mass_rate

        # This method requires discharge_pressure for the Newton iteration
        assert constraints.discharge_pressure is not None
        target_discharge_pressure = constraints.discharge_pressure

        result_mass_rate = find_root(
            lower_bound=minimum_mass_rate,
            upper_bound=maximum_mass_rate,
            func=lambda x: _calculate_train_result_given_mass_rate(mass_rate_kg_per_hour=x).discharge_pressure
            - target_discharge_pressure,
        )
        # This mass rate is the mass rate to use as mass rate after asv for each stage,
        # thus the asv in each stage should be set to correspond to this mass rate
        return _calculate_train_result_given_additional_mass_rate(
            additional_mass_rate_kg_per_hour=(result_mass_rate - minimum_mass_rate_kg_per_hour)
        )

    def find_fixed_shaft_speed_given_constraints(
        self,
        constraints: CompressorTrainEvaluationInput,
        lower_bound_for_speed: float | None = None,
        upper_bound_for_speed: float | None = None,
    ) -> float:
        """Calculate needed shaft speed to get desired outlet pressure

        Run compressor train forward model with inlet conditions and speed, and iterate on shaft speed until discharge
        pressure meets requested discharge pressure.

        Iteration (using brenth method) to find speed to meet requested discharge pressure

        The upper and lower bounds for the speed can be set, which is useful for a part of a compressor train that can
        share a common shaft with another part of a compressor train, which has another minimum and maximum speed.

        Iterative problem:
            f(speed) = calculate_compressor_train(speed).discharge_pressure - requested_discharge_pressure = 0
        Starting points for iterative method:
           speed_0 = minimum speed for train, calculate f(speed_0) aka f_0
           speed_1 = maximum speed for train, calculate f(speed_1) aka f_1

        Args:
            constraints (CompressorTrainEvaluationInput): The constraints for the evaluation.
            lower_bound_for_speed (float | None): The lower bound for the speed. If None, uses the minimum speed
            upper_bound_for_speed (float | None): The upper bound for the speed. If None, uses the maximum speed
        Returns:
            The speed required to operate at to meet the given constraints. (Bounded by the minimu and maximum speed)

        """
        minimum_speed = (
            lower_bound_for_speed
            if lower_bound_for_speed and lower_bound_for_speed > self.minimum_speed
            else self.minimum_speed
        )
        maximum_speed = (
            upper_bound_for_speed
            if upper_bound_for_speed and upper_bound_for_speed < self.maximum_speed
            else self.maximum_speed
        )

        def _calculate_compressor_train(_speed: float) -> CompressorTrainResultSingleTimeStep:
            self.shaft.set_speed(_speed)
            return self.calculate_compressor_train(
                constraints=constraints,
            )

        train_result_for_minimum_speed = _calculate_compressor_train(_speed=minimum_speed)
        train_result_for_maximum_speed = _calculate_compressor_train(_speed=maximum_speed)

        if not train_result_for_maximum_speed.within_capacity:
            # will not find valid result - the rate is above maximum rate, return invalid results at maximum speed
            self.shaft.set_speed(maximum_speed)
            return maximum_speed
        if not train_result_for_minimum_speed.within_capacity:
            # rate is above maximum rate for minimum speed. Find the lowest minimum speed which gives a valid result
            minimum_speed = -maximize_x_given_boolean_condition_function(
                x_min=-maximum_speed,
                x_max=-minimum_speed,
                bool_func=lambda x: _calculate_compressor_train(_speed=-x).within_capacity,
            )
            train_result_for_minimum_speed = _calculate_compressor_train(_speed=minimum_speed)

        # Solution 1, iterate on speed until target discharge pressure is found
        if (
            constraints.discharge_pressure is not None
            and train_result_for_minimum_speed.discharge_pressure
            <= constraints.discharge_pressure
            <= train_result_for_maximum_speed.discharge_pressure
        ):
            # At this point, discharge_pressure is confirmed to be not None
            target_discharge_pressure = constraints.discharge_pressure
            speed = find_root(
                lower_bound=minimum_speed,
                upper_bound=maximum_speed,
                func=lambda x: _calculate_compressor_train(_speed=x).discharge_pressure - target_discharge_pressure,
            )
            self.shaft.set_speed(speed)
            return speed

        # Solution 2, target pressure is too low:
        if (
            constraints.discharge_pressure is not None
            and constraints.discharge_pressure < train_result_for_minimum_speed.discharge_pressure
        ):
            self.shaft.set_speed(minimum_speed)
            return minimum_speed

        # Solution 3, target discharge pressure is too high
        self.shaft.set_speed(maximum_speed)
        return maximum_speed

    def split_train_on_stage_number(
        self,
        stage_number: int,
        pressure_control_first_part: FixedSpeedPressureControl | None = None,
        pressure_control_last_part: FixedSpeedPressureControl | None = None,
    ) -> tuple[
        Self,
        Self,
    ]:
        """
        Splits a variable speed compressor train into two sub-trains at the specified stage number.

        The first sub-train includes all stages before the split, and the second sub-train includes all stages from the split onward.
        Optionally, different pressure control strategies can be assigned to each sub-train.

        Args:
            stage_number: The stage index at which to split the train (0-based).
            pressure_control_first_part: Optional pressure control for the first sub-train.
            pressure_control_last_part: Optional pressure control for the second sub-train.

        Returns:
            Tuple containing:
                - The first sub-train (stages before the split).
                - The second sub-train (stages from the split onward).
        """

        # Create streams for first part
        assert isinstance(self._fluid_model, list)  # for mypy
        fluid_model_first_part = [
            fluid_model
            for port, fluid_model in zip(self.ports, self._fluid_model)
            if port.connected_to_stage_no < stage_number
        ]

        compressor_train_first_part = CompressorTrainCommonShaft(
            shaft=self.shaft,
            energy_usage_adjustment_constant=self.energy_usage_adjustment_constant,
            energy_usage_adjustment_factor=self.energy_usage_adjustment_factor,
            stages=self.stages[:stage_number],
            fluid_service=self._fluid_service,
            calculate_max_rate=self.calculate_max_rate if self.calculate_max_rate is not None else False,
            maximum_power=self.maximum_power,
            pressure_control=pressure_control_first_part,
            stage_number_interstage_pressure=self.stage_number_interstage_pressure,
        )

        compressor_train_first_part._fluid_model = fluid_model_first_part

        # Create streams for last part

        # Last part initially uses the main fluid factory (placeholder)
        # This will be updated at runtime after the fluid model (composition) is changed

        fluid_model_last_part = [deepcopy(self._fluid_model[0])]
        fluid_model_last_part.extend(
            [
                fluid_model
                for port, fluid_model in zip(self.ports, self._fluid_model)
                if port.connected_to_stage_no >= stage_number
            ]
        )

        compressor_train_last_part = CompressorTrainCommonShaft(
            energy_usage_adjustment_constant=self.energy_usage_adjustment_constant,
            energy_usage_adjustment_factor=self.energy_usage_adjustment_factor,
            stages=self.stages[stage_number:],
            fluid_service=self._fluid_service,
            shaft=self.shaft,
            calculate_max_rate=self.calculate_max_rate if self.calculate_max_rate is not None else False,
            maximum_power=self.maximum_power,
            pressure_control=pressure_control_last_part,
            stage_number_interstage_pressure=self.stage_number_interstage_pressure,
        )
        compressor_train_last_part._fluid_model = fluid_model_last_part

        return compressor_train_first_part, compressor_train_last_part

    def split_rates_on_stage_number(
        self,
        rates_per_stream: list[float],
        stage_number: int,
    ) -> tuple[list[float], list[float]]:
        """
        Splits the stream rates for a compressor train into two lists at the specified stage number.

        The first list contains rates for streams connected to stages before the split.
        The second list contains the rate at the split stage and rates for streams connected to stages at or after the split.

        Args:
            rates_per_stream: List of rates for each stream in the compressor train.
            stage_number: The stage index at which to split the rates (0-based).

        Returns:
            Tuple containing:
                - List of rates for the first part (before the split stage).
                - List of rates for the last part (from the split stage onward).
        """
        rates_first_part = [
            rates_per_stream[i] for i, port in enumerate(self.ports) if port.connected_to_stage_no < stage_number
        ]

        rate_at_outlet_first_part = sum(
            rates_per_stream[i] if port.is_inlet_port else -rates_per_stream[i]
            for i, port in enumerate(self.ports)
            if port.connected_to_stage_no < stage_number
        )

        rates_last_part = [rate_at_outlet_first_part]

        for i, port in enumerate(self.ports):
            if port.connected_to_stage_no >= stage_number:
                rates_last_part.append(rates_per_stream[i])

        return rates_first_part, rates_last_part

    def find_and_calculate_for_compressor_train_with_two_pressure_requirements(
        self,
        stage_number_for_intermediate_pressure_target: int | None,
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
        # This method requires stream_rates to be set for splitting operations
        assert constraints.rates is not None
        assert stage_number_for_intermediate_pressure_target is not None

        # Split train into two and calculate minimum speed to reach required pressures
        compressor_train_first_part, compressor_train_last_part = self.split_train_on_stage_number(
            stage_number=stage_number_for_intermediate_pressure_target,
            pressure_control_first_part=pressure_control_first_part,
            pressure_control_last_part=pressure_control_last_part,
        )

        std_rates_first_part, std_rates_last_part = self.split_rates_on_stage_number(
            rates_per_stream=constraints.rates,
            stage_number=stage_number_for_intermediate_pressure_target,
        )
        constraints_first_part = CompressorTrainEvaluationInput(
            suction_pressure=constraints.suction_pressure,
            discharge_pressure=constraints.interstage_pressure,
            rates=std_rates_first_part,
        )
        constraints_last_part = CompressorTrainEvaluationInput(
            suction_pressure=constraints.interstage_pressure,
            discharge_pressure=constraints.discharge_pressure,
            rates=std_rates_last_part,
        )

        # Get the speed found for the first part - will be used to compare with the last part
        shaft_speed_first_part = compressor_train_first_part.find_fixed_shaft_speed_given_constraints(
            constraints=constraints_first_part,
            lower_bound_for_speed=self.minimum_speed,  # Only search for a solution within the bounds of the
            upper_bound_for_speed=self.maximum_speed,  # original, complete compressor train
        )

        if math.isclose(shaft_speed_first_part, self.minimum_speed, rel_tol=EPSILON):
            compressor_train_results_first_part_with_optimal_speed_result = (
                compressor_train_first_part.evaluate_with_pressure_control_given_constraints(
                    constraints=constraints_first_part,
                )
            )
        else:
            compressor_train_results_first_part_with_optimal_speed_result = (
                compressor_train_first_part.calculate_compressor_train(
                    constraints=constraints_first_part,
                )
            )

        assert isinstance(compressor_train_last_part._fluid_model, list)  # for mypy
        compressor_train_last_part._fluid_model[0] = FluidModel(
            composition=compressor_train_results_first_part_with_optimal_speed_result.stage_results[
                -1
            ].outlet_stream.composition,
            eos_model=compressor_train_results_first_part_with_optimal_speed_result.stage_results[
                -1
            ].outlet_stream.fluid_model.eos_model,
        )

        # Get the speed found for the last part - will be used to compare with the first part
        shaft_speed_last_part = compressor_train_last_part.find_fixed_shaft_speed_given_constraints(
            constraints=constraints_last_part,
            lower_bound_for_speed=self.minimum_speed,
            upper_bound_for_speed=self.maximum_speed,
        )

        if math.isclose(shaft_speed_last_part, self.minimum_speed, rel_tol=EPSILON):
            compressor_train_results_last_part_with_optimal_speed_result = (
                compressor_train_last_part.evaluate_with_pressure_control_given_constraints(
                    constraints=constraints_last_part,
                )
            )
        else:
            compressor_train_results_last_part_with_optimal_speed_result = (
                compressor_train_last_part.calculate_compressor_train(
                    constraints=constraints_last_part,
                )
            )

        """
        Determine which of the first and last part will govern the speed to use
        Then run the last part as a single speed train with the speed chosen
        Fixme: Need to deliver the result in a proper format below.
        """
        if shaft_speed_first_part > shaft_speed_last_part:
            compressor_train_last_part.shaft.set_speed(shaft_speed_first_part)
            compressor_train_results_last_part_with_pressure_control = (
                compressor_train_last_part.evaluate_with_pressure_control_given_constraints(
                    constraints=constraints_last_part,
                )
            )
            compressor_train_results_to_return_first_part = (
                compressor_train_results_first_part_with_optimal_speed_result
            )
            compressor_train_results_to_return_last_part = compressor_train_results_last_part_with_pressure_control

        else:
            compressor_train_first_part.shaft.set_speed(shaft_speed_last_part)
            compressor_train_results_first_part_with_pressure_control = (
                compressor_train_first_part.evaluate_with_pressure_control_given_constraints(
                    constraints=constraints_first_part,
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
            constraints=constraints,
            results=train_result,
        )

        train_result.target_pressure_status = target_pressure_status

        return train_result

    @staticmethod
    def _check_intermediate_pressure_stage_number_is_valid(
        _stage_number_intermediate_pressure: int | None,
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
