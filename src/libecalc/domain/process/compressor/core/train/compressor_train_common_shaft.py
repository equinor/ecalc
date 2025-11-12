from functools import partial

from libecalc.common.errors.exceptions import EcalcError, IllegalStateException
from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl
from libecalc.common.logger import logger
from libecalc.domain.component_validation_error import (
    ProcessChartTypeValidationException,
    ProcessDischargePressureValidationException,
)
from libecalc.domain.process.compressor.core.results import (
    CompressorTrainResultSingleTimeStep,
    CompressorTrainStageResultSingleTimeStep,
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
from libecalc.domain.process.value_objects.fluid_stream import ProcessConditions


class CompressorTrainCommonShaft(CompressorTrainModel):
    """A model of a compressor train with one or multiple compressor stages on a common shaft.

    In general, a compressor train (series of compressors) is running on a single shaft, meaning each stage will always
    have the same speed. Given inlet fluid conditions (composition, temperature, pressure, rate) and a shaft speed, the
    intermediate pressures (and temperature before cooling) between stages and the outlet pressure (and temperature) is
    given.

    Args:
        fluid_factory (FluidFactoryInterface): Factory to create fluid streams and thermo systems
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
    def is_variable_speed(self):
        return all(stage.compressor.compressor_chart.is_variable_speed for stage in self.stages)

    def evaluate_given_constraints(
        self,
        constraints: CompressorTrainEvaluationInput,
        fixed_speed: float | None = None,
    ) -> CompressorTrainResultSingleTimeStep:
        if constraints.rate > 0:  # type: ignore[operator]
            if fixed_speed is None:
                fixed_speed = self.find_fixed_shaft_speed_given_constraints(constraints=constraints)
            self.shaft.set_speed(fixed_speed)
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
        asv_rate_fraction: float = 0.0,
        asv_additional_mass_rate: float = 0.0,
    ) -> CompressorTrainResultSingleTimeStep:
        """Calculate compressor train result given inlet conditions and speed

        Args:
            constraints (CompressorTrainEvaluationInput): The constraints for the evaluation.
            asv_rate_fraction:
            asv_additional_mass_rate:

        Returns:
            results including conditions and calculations for each stage and power.

        """
        if not self.shaft.speed_is_defined or constraints.rate is None or constraints.suction_pressure is None:
            raise EcalcError(
                title="Missing required parameters",
                message="Compressor train calculation requires speed, rate and suction pressure to be set.",
            )
        # Initialize stream at inlet of first compressor stage using fluid properties and inlet conditions

        train_inlet_stream = self.train_inlet_stream(
            pressure=constraints.suction_pressure,
            temperature=self.stages[0].inlet_temperature_kelvin,
            rate=constraints.rate,
        )

        stage_results: list[CompressorTrainStageResultSingleTimeStep] = []
        outlet_stream = train_inlet_stream
        for stage in self.stages:
            inlet_stream = outlet_stream
            stage_result = stage.evaluate(
                inlet_stream_stage=inlet_stream,
                speed=self.shaft.get_speed(),
                asv_rate_fraction=asv_rate_fraction,
                asv_additional_mass_rate=asv_additional_mass_rate,
            )
            stage_results.append(stage_result)

            # We need to recreate the domain object from the result object. This needs cleaning up.
            outlet_stream = stage_result.outlet_stream
        # check if target pressures are met
        target_pressure_status = self.check_target_pressures(
            constraints=constraints,
            results=stage_results,
        )

        return CompressorTrainResultSingleTimeStep(
            inlet_stream=train_inlet_stream,
            outlet_stream=outlet_stream,
            stage_results=stage_results,
            speed=self.shaft.get_speed(),
            above_maximum_power=sum([stage_result.power_megawatt for stage_result in stage_results])
            > self.maximum_power
            if self.maximum_power
            else False,
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
            constraints (CompressorTrainEvaluationInput: The constraints for the evaluation.
            allow_asv:

        Returns:
            Standard volume rate [Sm3/day]

        """
        inlet_density = self._fluid_factory.create_thermo_system(
            pressure_bara=constraints.suction_pressure,  # type: ignore[arg-type]
            temperature_kelvin=self.stages[0].inlet_temperature_kelvin,
        ).density

        def _calculate_train_result(mass_rate: float, speed: float) -> CompressorTrainResultSingleTimeStep:
            """Partial function of self.calculate_compressor_train_given_speed
            where we only pass mass_rate.
            """
            self.shaft.set_speed(speed)
            return self.calculate_compressor_train(
                constraints=constraints.create_conditions_with_new_input(
                    new_rate=self._fluid_factory.mass_rate_to_standard_rate(mass_rate),  # type: ignore[arg-type]
                )
            )

        def _calculate_train_result_given_ps_pd(mass_rate: float) -> CompressorTrainResultSingleTimeStep:
            """Partial function of self.evaluate_given_constraints
            where we only pass mass_rate.
            """
            return self.evaluate_given_constraints(
                constraints=constraints.create_conditions_with_new_input(
                    new_rate=self._fluid_factory.mass_rate_to_standard_rate(mass_rate),  # type: ignore[arg-type]
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
                    new_rate=self._fluid_factory.mass_rate_to_standard_rate(_max_valid_mass_rate_at_given_speed),  # type: ignore[arg-type]
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
            result = self._fluid_factory.mass_rate_to_standard_rate(rate_to_return)
            return float(result)
        elif (
            self.evaluate_given_constraints(
                constraints=constraints.create_conditions_with_new_input(
                    new_rate=self._fluid_factory.mass_rate_to_standard_rate(rate_to_return),  # type: ignore[arg-type]
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

                result = self._fluid_factory.mass_rate_to_standard_rate(
                    find_root(
                        lower_bound=result_with_minimum_rate.stage_results[0].mass_rate_asv_corrected_kg_per_hour,
                        upper_bound=rate_to_return,
                        func=lambda x: self.evaluate_given_constraints(
                            constraints=constraints.create_conditions_with_new_input(
                                new_rate=self._fluid_factory.mass_rate_to_standard_rate(x),  # type: ignore[arg-type]
                            )
                        ).power_megawatt
                        - maximum_power * (1 - POWER_CALCULATION_TOLERANCE),
                        relative_convergence_tolerance=1e-3,
                        maximum_number_of_iterations=20,
                    )
                )
                return float(result)
        else:
            # maximum power defined, but found rate is below maximum power
            result = self._fluid_factory.mass_rate_to_standard_rate(rate_to_return)
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
            train_result.outlet_stream = train_result.outlet_stream.create_stream_with_new_conditions(
                conditions=ProcessConditions(
                    pressure_bara=constraints.discharge_pressure,
                    temperature_kelvin=train_result.outlet_stream.temperature_kelvin,
                )
            )
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
        assert constraints.rate is not None
        assert constraints.suction_pressure is not None

        train_inlet_stream = self.train_inlet_stream(
            pressure=constraints.suction_pressure,
            temperature=self.stages[0].inlet_temperature_kelvin,
            rate=constraints.rate,
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
            return self.calculate_compressor_train(
                constraints=constraints,
                asv_rate_fraction=asv_rate_fraction,
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

        # Multiple streams factories are lists (one per stream).
        if isinstance(self._fluid_factory, list):
            fluid_factory = self._fluid_factory[0]
        else:
            fluid_factory = self._fluid_factory

        inlet_stream_train = fluid_factory.create_stream_from_standard_rate(
            pressure_bara=constraints.suction_pressure,
            temperature_kelvin=self.stages[0].inlet_temperature_kelvin,
            standard_rate_m3_per_day=constraints.rate,  # type: ignore[arg-type]
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
        # Multiple streams factories are lists (one per stream).
        if isinstance(self._fluid_factory, list):
            fluid_factory = self._fluid_factory[0]
        else:
            fluid_factory = self._fluid_factory
        minimum_mass_rate_kg_per_hour = fluid_factory.standard_rate_to_mass_rate(
            standard_rate_m3_per_day=constraints.rate,  # type: ignore[arg-type]
        )
        # Iterate on rate until pressures are met
        density_train_inlet_fluid = fluid_factory.create_thermo_system(
            pressure_bara=constraints.suction_pressure,  # type: ignore[arg-type]
            temperature_kelvin=self.stages[0].inlet_temperature_kelvin,
        ).density

        def _calculate_train_result_given_mass_rate(
            mass_rate_kg_per_hour: float,
        ) -> CompressorTrainResultSingleTimeStep:
            return self.calculate_compressor_train(
                constraints=constraints.create_conditions_with_new_input(
                    new_rate=fluid_factory.mass_rate_to_standard_rate(mass_rate_kg_per_h=mass_rate_kg_per_hour),  # type: ignore[arg-type]
                ),
            )

        def _calculate_train_result_given_additional_mass_rate(
            additional_mass_rate_kg_per_hour: float,
        ) -> CompressorTrainResultSingleTimeStep:
            return self.calculate_compressor_train(
                constraints=constraints,
                asv_additional_mass_rate=additional_mass_rate_kg_per_hour,
            )

        # outer bounds for minimum and maximum mass rate without individual recirculation on stages will be the
        # minimum and maximum mass rate for the first stage, adjusted for the volume entering the first stage
        minimum_mass_rate = max(
            minimum_mass_rate_kg_per_hour,
            self.stages[0].compressor.compressor_chart.minimum_rate * density_train_inlet_fluid,
        )  # type: ignore[type-var]
        # note: we subtract EPSILON to avoid floating point issues causing the maximum mass rate to exceed chart area maximum rate after round-trip conversion (mass rate -> standard rat -> mass rate)
        maximum_mass_rate = (
            self.stages[0].compressor.compressor_chart.maximum_rate * density_train_inlet_fluid * (1 - EPSILON)
        )

        # if the minimum_mass_rate_kg_per_hour(i.e. before increasing rate with recirculation to lower pressure)
        # is already larger than the maximum mass rate, there is no need for optimization - just add result
        # with minimum_mass_rate_kg_per_hour (which will fail with above maximum flow rate)
        if minimum_mass_rate_kg_per_hour > maximum_mass_rate:
            return _calculate_train_result_given_mass_rate(mass_rate_kg_per_hour=minimum_mass_rate_kg_per_hour)  # type: ignore[arg-type]

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
                x_max=-minimum_mass_rate,  # type: ignore[arg-type]
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
                mass_rate_kg_per_hour=minimum_mass_rate + inc * (maximum_mass_rate - minimum_mass_rate)  # type: ignore[arg-type]
            )
            while not train_result_for_mass_rate.mass_rate_asv_corrected_is_constant_for_stages:
                inc += 0.1
                if inc >= 1:
                    logger.error("Single speed train with Common ASV pressure control has no solution!")
                train_result_for_mass_rate = _calculate_train_result_given_mass_rate(
                    mass_rate_kg_per_hour=minimum_mass_rate + inc * (maximum_mass_rate - minimum_mass_rate)  # type: ignore[arg-type]
                )

            # found one solution, now find min and max
            minimum_mass_rate = -maximize_x_given_boolean_condition_function(
                x_min=-(minimum_mass_rate + inc * (maximum_mass_rate - minimum_mass_rate)),  # type: ignore[arg-type]
                x_max=-minimum_mass_rate,  # type: ignore[arg-type]
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
            lower_bound=minimum_mass_rate,  # type: ignore[arg-type]
            upper_bound=maximum_mass_rate,
            func=lambda x: _calculate_train_result_given_mass_rate(mass_rate_kg_per_hour=x).discharge_pressure
            - target_discharge_pressure,
        )
        # This mass rate is the mass rate to use as mass rate after asv for each stage,
        # thus the asv in each stage should be set to correspond to this mass rate
        return _calculate_train_result_given_additional_mass_rate(
            additional_mass_rate_kg_per_hour=(result_mass_rate - minimum_mass_rate_kg_per_hour)  # type: ignore[arg-type]
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

            return speed

        # Solution 2, target pressure is too low:
        if (
            constraints.discharge_pressure is not None
            and constraints.discharge_pressure < train_result_for_minimum_speed.discharge_pressure
        ):
            return minimum_speed

        # Solution 3, target discharge pressure is too high
        return maximum_speed
