from copy import deepcopy
from functools import partial
from typing import List, Optional

import numpy as np
from numpy.typing import NDArray

from libecalc import dto
from libecalc.common.errors.exceptions import EcalcError, IllegalStateException
from libecalc.common.logger import logger
from libecalc.common.units import UnitConstants
from libecalc.core.models.compressor.results import (
    CompressorTrainResultSingleTimeStep,
    CompressorTrainStageResultSingleTimeStep,
)
from libecalc.core.models.compressor.train.base import CompressorTrainModel
from libecalc.core.models.compressor.train.fluid import FluidStream
from libecalc.core.models.compressor.train.single_speed_compressor_train_common_shaft import (
    SingleSpeedCompressorTrainCommonShaft,
)
from libecalc.core.models.compressor.train.stage import CompressorTrainStage
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
from libecalc.core.models.results.compressor import (
    CompressorTrainCommonShaftFailureStatus,
)
from libecalc.dto.types import FixedSpeedPressureControl

EPSILON = 1e-5


class VariableSpeedCompressorTrainCommonShaft(CompressorTrainModel):
    """A model of a compressor train with variable speed

    In general, a compressor train (series of compressors) is running on a single shaft, meaning each stage will always
    have the same speed. Given inlet fluid conditions (composition, temperature, pressure, rate) and a shaft speed, the
    intermediate pressures (and temperature before cooling) between stages and the outlet pressure (and temperature) is
    given. To solve this for a given outlet pressure, one must iterate to find the speed.

    Compressor charts:
    The compressor charts must be pre-defined and have variable speed. Each compressor chart may either be
    1. Using a generic chart by specifying a design point
    2. Fully specified compressor chart

    FluidStream:
    Model of the fluid. See FluidStream
    For each stage, one must specify a compressor chart, an inlet temperature and whether to take out liquids after
    compression and cooling. In addition, one must specify the pressure drop from previous stage (It may be 0).
    The compressor train may be evaluated by one inlet through the entire train (fluid spec and rate), or by specifying
    one fluid stream per stage (to support incoming or outgoing streams between stages).

    """

    def __init__(
        self,
        data_transfer_object: dto.VariableSpeedCompressorTrain,
    ):
        logger.debug(
            f"Creating VariableSpeedCompressorTrainCommonShaft with n_stages: {len(data_transfer_object.stages)}"
        )
        super().__init__(data_transfer_object)
        self.data_transfer_object = data_transfer_object

    @property
    def number_of_compressor_stages(self) -> int:
        return len(self.stages)

    def _evaluate_rate_ps_pd(
        self,
        rate: NDArray[np.float64],
        suction_pressure: NDArray[np.float64],
        discharge_pressure: NDArray[np.float64],
    ) -> List[CompressorTrainResultSingleTimeStep]:
        mass_rate_kg_per_hour = self.fluid.standard_rate_to_mass_rate(standard_rates=rate)

        # Iterate over input points, calculate one by one
        train_results: List[CompressorTrainResultSingleTimeStep] = []
        for (
            mass_rate_kg_per_hour_this_time_step,
            suction_pressure_this_time_step,
            discharge_pressure_this_time_step,
        ) in zip(mass_rate_kg_per_hour, suction_pressure, discharge_pressure):
            if mass_rate_kg_per_hour_this_time_step > 0:
                compressor_train_result_single_time_step = self.calculate_shaft_speed_given_rate_ps_pd(
                    mass_rate_kg_per_hour=mass_rate_kg_per_hour_this_time_step,
                    suction_pressure=suction_pressure_this_time_step,
                    target_discharge_pressure=discharge_pressure_this_time_step,
                )
                train_results.append(compressor_train_result_single_time_step)
            else:
                train_results.append(
                    CompressorTrainResultSingleTimeStep.create_empty(number_of_stages=len(self.stages))
                )

        return train_results

    def calculate_shaft_speed_given_rate_ps_pd(
        self,
        mass_rate_kg_per_hour: float,
        suction_pressure: float,
        target_discharge_pressure: float,
    ) -> CompressorTrainResultSingleTimeStep:
        """Calculate needed shaft speed to get desired outlet pressure

        Run compressor train forward model with inlet conditions and speed, and iterate on shaft speed until discharge
        pressure meets requested discharge pressure.

        Iteration (using brenth method) to find speed to meet requested discharge pressure

        Iterative problem:
            f(speed) = calculate_compressor_train(speed).discharge_pressure - requested_discharge_pressure = 0
        Starting points for iterative method:
           speed_0 = minimum speed for train, calculate f(speed_0) aka f_0
           speed_1 = maximum speed for train, calculate f(speed_1) aka f_1

        Args:
            mass_rate_kg_per_hour: Mass rate of flow through compressor [kg/h]
            suction_pressure: Inlet pressure [bara]
            target_discharge_pressure: Outlet pressure [bara]

        Returns:
            Train results corresponding to resulting final speed

        """

        def _calculate_train_result_given_rate_ps_speed(_speed: float) -> CompressorTrainResultSingleTimeStep:
            return self.calculate_compressor_train_given_rate_ps_speed(
                inlet_pressure_bara=suction_pressure,
                mass_rate_kg_per_hour=mass_rate_kg_per_hour,
                speed=_speed,
            )

        minimum_speed = self.minimum_speed
        train_result_for_minimum_speed = _calculate_train_result_given_rate_ps_speed(_speed=minimum_speed)
        train_result_for_maximum_speed = _calculate_train_result_given_rate_ps_speed(_speed=self.maximum_speed)

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
                lower_bound=self.minimum_speed,
                upper_bound=self.maximum_speed,
                func=lambda x: _calculate_train_result_given_rate_ps_speed(_speed=x).discharge_pressure
                - target_discharge_pressure,
            )

            return _calculate_train_result_given_rate_ps_speed(_speed=speed)

        # Solution 2, target pressure is too low:
        if target_discharge_pressure < train_result_for_minimum_speed.discharge_pressure:
            if self.pressure_control:
                return self.calculate_compressor_train_given_rate_ps_pd_speed(
                    speed=minimum_speed,
                    mass_rate_kg_per_hour=mass_rate_kg_per_hour,
                    inlet_pressure=suction_pressure,
                    outlet_pressure=target_discharge_pressure,
                )
            train_result_for_minimum_speed.failure_status = (
                CompressorTrainCommonShaftFailureStatus.TARGET_DISCHARGE_PRESSURE_TOO_LOW
            )
            return train_result_for_minimum_speed

        # Solution 3, target discharge pressure is too high
        train_result_for_maximum_speed.failure_status = (
            CompressorTrainCommonShaftFailureStatus.TARGET_DISCHARGE_PRESSURE_TOO_HIGH
        )
        return train_result_for_maximum_speed

    def calculate_compressor_train_given_rate_ps_speed(
        self,
        mass_rate_kg_per_hour: float,
        inlet_pressure_bara: float,
        speed: float,
        asv_rate_fraction: float = 0.0,
        asv_additional_mass_rate: float = 0.0,
    ) -> CompressorTrainResultSingleTimeStep:
        """Calculate compressor train result given inlet conditions and speed

        Args:
            mass_rate_kg_per_hour: [kg/h]
            inlet_pressure_bara: [bara]
            speed: Shaft speed [rpm]
            asv_rate_fraction:
            asv_additional_mass_rate:

        Returns:
            results including conditions and calculations for each stage and power.

        """

        # Initialize stream at inlet of first compressor stage using fluid properties and inlet conditions
        train_inlet_stream = self.fluid.get_fluid_streams(
            pressure_bara=np.asarray([inlet_pressure_bara - self.stages[0].pressure_drop_ahead_of_stage]),
            temperature_kelvin=np.asarray([self.stages[0].inlet_temperature_kelvin]),
        )[0]

        stage_results: List[CompressorTrainStageResultSingleTimeStep] = []
        outlet_stream = train_inlet_stream
        for stage in self.stages:
            inlet_stream = outlet_stream

            stage_result = stage.evaluate(
                inlet_stream_stage=inlet_stream,
                speed=speed,
                mass_rate_kg_per_hour=mass_rate_kg_per_hour,
                asv_rate_fraction=asv_rate_fraction,
                asv_additional_mass_rate=asv_additional_mass_rate,
            )
            stage_results.append(stage_result)

            # We need to recreate the domain object from the result object. This needs cleaning up.
            outlet_stream = inlet_stream.set_new_pressure_and_temperature(
                new_pressure_bara=stage_result.outlet_stream.pressure_bara,
                new_temperature_kelvin=stage_result.outlet_stream.temperature_kelvin,
            )

        return CompressorTrainResultSingleTimeStep(stage_results=stage_results, speed=speed)

    def get_max_standard_rate(
        self,
        suction_pressures: NDArray[np.float64],
        discharge_pressures: NDArray[np.float64],
    ) -> NDArray[np.float64]:
        """Calculate the max standard rate [Sm3/day] that the compressor train can operate at.

        Args:
            suction_pressures: List of suction pressures [bara]
            discharge_pressures: List of discharge pressures [bara]

        Returns:
            List of maximum standard rates corresponding to given inlet and outlet pressures [Sm3/day]

        """
        inlet_streams = self.fluid.get_fluid_streams(
            pressure_bara=suction_pressures,
            temperature_kelvin=np.full_like(suction_pressures, fill_value=self.stages[0].inlet_temperature_kelvin),
        )

        max_mass_rates = []
        for suction_pressure, discharge_pressure, inlet_stream in zip(
            suction_pressures, discharge_pressures, inlet_streams
        ):
            try:
                max_mass_rate = self._get_max_mass_rate_single_timestep(
                    suction_pressure=suction_pressure,
                    target_discharge_pressure=discharge_pressure,
                    inlet_stream=inlet_stream,
                )
            except EcalcError as e:
                logger.exception(e)
                max_mass_rate = np.nan

            max_mass_rates.append(max_mass_rate)

        return np.array(self.fluid.mass_rate_to_standard_rate(mass_rate_kg_per_hour=np.array(max_mass_rates)))

    def _get_max_mass_rate_single_timestep(
        self,
        suction_pressure: float,
        target_discharge_pressure: float,
        inlet_stream: FluidStream,
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
            suction_pressure: Suction pressure per time step [bara]
            target_discharge_pressure: Discharge pressure per time step [bara]
            inlet_stream:
            allow_asv:

        Returns:
            Standard volume rate [Sm3/day]

        """
        inlet_density = inlet_stream.density

        def _calculate_train_result(mass_rate: float, speed: float) -> CompressorTrainResultSingleTimeStep:
            """Partial function of self.calculate_compressor_train_given_rate_ps_speed
            where we only pass mass_rate and speed.
            """
            return self.calculate_compressor_train_given_rate_ps_speed(
                inlet_pressure_bara=suction_pressure,
                mass_rate_kg_per_hour=mass_rate,
                speed=speed,
            )

        def _calculate_train_result_given_speed_at_stone_wall(
            speed: float,
        ) -> CompressorTrainResultSingleTimeStep:
            """Partial function of self.calculate_compressor_train_given_rate_ps_speed.
            Same as above, but mass rate is pinned to the "stone wall" as a function of speed.
            """
            _max_valid_mass_rate_at_given_speed = maximize_x_given_boolean_condition_function(
                x_min=self.stages[0].compressor_chart.minimum_rate_as_function_of_speed(speed) * inlet_density,  # or 0?
                x_max=self.stages[0].compressor_chart.maximum_rate_as_function_of_speed(speed) * inlet_density,
                bool_func=lambda x: _calculate_train_result(mass_rate=x, speed=speed).is_valid,
                convergence_tolerance=1e-3,
                maximum_number_of_iterations=20,
            )

            return self.calculate_compressor_train_given_rate_ps_speed(
                inlet_pressure_bara=suction_pressure,
                mass_rate_kg_per_hour=_max_valid_mass_rate_at_given_speed,
                speed=speed,
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
            self.stages[0].compressor_chart.maximum_speed_curve.minimum_rate * inlet_density
        )
        max_mass_rate_at_max_speed_first_stage = (
            self.stages[0].compressor_chart.maximum_speed_curve.maximum_rate * inlet_density
        )
        max_mass_rate_at_min_speed_first_stage = (
            self.stages[0].compressor_chart.maximum_rate_as_function_of_speed(
                self.stages[0].compressor_chart.minimum_speed
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
        if not result_min_mass_rate_at_max_speed_first_stage.is_valid:
            if allow_asv:
                min_mass_rate_at_max_speed = EPSILON
                result_min_mass_rate_at_max_speed = _calculate_train_result_at_max_speed_given_mass_rate(
                    mass_rate=min_mass_rate_at_max_speed
                )
                if not result_min_mass_rate_at_max_speed.is_valid:
                    logger.debug(
                        "There are no valid mass rate for VariableSpeedCompressorTrain."
                        "Infeasible solution. Returning max rate 0.0 (None)."
                    )
                    return 0.0
                max_mass_rate_at_max_speed = maximize_x_given_boolean_condition_function(
                    x_min=EPSILON,
                    x_max=min_mass_rate_at_max_speed_first_stage,
                    bool_func=lambda x: _calculate_train_result_at_max_speed_given_mass_rate(mass_rate=x).is_valid,
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
            if not result_max_mass_rate_at_max_speed_first_stage.is_valid:
                max_mass_rate_at_max_speed = maximize_x_given_boolean_condition_function(
                    x_min=min_mass_rate_at_max_speed,
                    x_max=max_mass_rate_at_max_speed_first_stage,
                    bool_func=lambda x: _calculate_train_result_at_max_speed_given_mass_rate(mass_rate=x).is_valid,
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
        if result_min_mass_rate_at_max_speed.discharge_pressure < target_discharge_pressure:
            return 0.0

        # Solution scenario 2. Solution is at maximum speed curve.
        elif target_discharge_pressure >= result_max_mass_rate_at_max_speed.discharge_pressure:
            """
            Iterating along max speed curve for first stage.
            """
            result_mass_rate = find_root(
                lower_bound=min_mass_rate_at_max_speed,
                upper_bound=max_mass_rate_at_max_speed,
                func=lambda x: _calculate_train_result_at_max_speed_given_mass_rate(mass_rate=x).discharge_pressure
                - target_discharge_pressure,
                relative_convergence_tolerance=1e-3,
                maximum_number_of_iterations=20,
            )
            rate_to_return = result_mass_rate * (1 - RATE_CALCULATION_TOLERANCE)

        # Solution 3: If solution not found along max speed curve,
        # run at max_mass_rate, but using the defined pressure control.
        elif (
            self.data_transfer_object.pressure_control is not None
            and self.calculate_compressor_train_given_rate_ps_pd_speed(
                speed=self.maximum_speed,
                inlet_pressure=suction_pressure,
                outlet_pressure=target_discharge_pressure,
                mass_rate_kg_per_hour=max_mass_rate_at_max_speed,
            ).is_valid
        ):
            rate_to_return = max_mass_rate_at_max_speed * (1 - RATE_CALCULATION_TOLERANCE)

        # Solution scenario 4. Solution at the "Stone wall".
        else:
            # Ensuring that the maximum mass rate at min speed is valid for the whole train.
            if not result_max_mass_rate_at_min_speed_first_stage.is_valid:
                max_mass_rate_at_min_speed = maximize_x_given_boolean_condition_function(
                    x_min=EPSILON,
                    x_max=max_mass_rate_at_min_speed_first_stage,
                    bool_func=lambda x: _calculate_train_result_at_min_speed_given_mass_rate(mass_rate=x).is_valid,
                )
                result_max_mass_rate_at_min_speed = _calculate_train_result_at_min_speed_given_mass_rate(
                    mass_rate=max_mass_rate_at_min_speed
                )
            else:
                # max_mass_rate_at_min_speed = max_mass_rate_at_max_speed_first_stage
                result_max_mass_rate_at_min_speed = result_max_mass_rate_at_min_speed_first_stage

            if (
                result_max_mass_rate_at_max_speed.discharge_pressure
                >= target_discharge_pressure
                >= result_max_mass_rate_at_min_speed.discharge_pressure
            ):
                # iterate along stone wall until target discharge pressure is reached
                result_speed = find_root(
                    lower_bound=self.minimum_speed,
                    upper_bound=self.maximum_speed,
                    func=lambda x: _calculate_train_result_given_speed_at_stone_wall(speed=x).discharge_pressure
                    - target_discharge_pressure,
                )
                compressor_train_result = _calculate_train_result_given_speed_at_stone_wall(speed=result_speed)

                rate_to_return = compressor_train_result.mass_rate_kg_per_hour * (1 - RATE_CALCULATION_TOLERANCE)

            # Solution scenario 5. Too high pressure even at min speed and max flow rate.
            elif result_max_mass_rate_at_min_speed.discharge_pressure > target_discharge_pressure:
                return 0.0
            else:
                msg = "You should not end up here. Please contact eCalc support."
                logger.exception(msg)
                raise IllegalStateException(msg)

        # Check that rate_to_return, suction_pressure and discharge_pressure does not require too much power.
        # If so, reduce rate such that power comes below maximum power
        if not self.data_transfer_object.maximum_power:
            return rate_to_return
        elif (
            self.calculate_shaft_speed_given_rate_ps_pd(
                mass_rate_kg_per_hour=rate_to_return,
                suction_pressure=suction_pressure,
                target_discharge_pressure=target_discharge_pressure,
            ).power_megawatt
            > self.data_transfer_object.maximum_power
        ):
            # check if minimum_rate gives too high power consumption
            result_with_minimum_rate = self.calculate_shaft_speed_given_rate_ps_pd(
                mass_rate_kg_per_hour=EPSILON,
                suction_pressure=suction_pressure,
                target_discharge_pressure=target_discharge_pressure,
            )
            if result_with_minimum_rate.power_megawatt > self.data_transfer_object.maximum_power:
                return 0.0  # can't find solution
            else:
                # iterate between rate with minimum power, and the previously found rate to return, to find the
                # maximum rate that gives power consumption below maximum power
                return find_root(
                    lower_bound=result_with_minimum_rate.mass_rate_asv_corrected_kg_per_hour,
                    upper_bound=rate_to_return,
                    func=lambda x: self.evaluate_rate_ps_pd(
                        rate=np.asarray([self.fluid.mass_rate_to_standard_rate(x)]),
                        suction_pressure=np.asarray([suction_pressure]),
                        discharge_pressure=np.asarray([target_discharge_pressure]),
                    ).power[0]
                    - self.data_transfer_object.maximum_power * (1 - POWER_CALCULATION_TOLERANCE),
                    relative_convergence_tolerance=1e-3,
                    maximum_number_of_iterations=20,
                )
        else:
            # maximum power defined, but found rate is below maximum power
            return rate_to_return

    def calculate_compressor_train_given_rate_pd_speed(
        self,
        speed: float,
        outlet_pressure: float,
        mass_rate_kg_per_hour: float,
        upper_bound_for_inlet_pressure: Optional[float] = None,
    ) -> CompressorTrainResultSingleTimeStep:
        """Calculate compressor train result given a single shaft speed, outlet pressure and mass rate

        Iterative method used to find inlet pressure corresponding to given shaft speed, outlet pressure and mass rate

        Args:
            speed: Shaft speed [rpm]
            outlet_pressure: Outlet pressure [bara]
            mass_rate_kg_per_hour: mass rate through the compressor train [kg/h]
            upper_bound_for_inlet_pressure: Optional maximum inlet pressure [bara], otherwise outlet pressure is used as upper bound

        Returns:
            Compressor train result for given timestep

        """

        def _calculate_train_result_given_rate_ps_speed(
            _inlet_pressure: float,
        ) -> CompressorTrainResultSingleTimeStep:
            return self.calculate_compressor_train_given_rate_ps_speed(
                inlet_pressure_bara=_inlet_pressure,
                mass_rate_kg_per_hour=mass_rate_kg_per_hour,
                speed=speed,
            )

        choked_inlet_pressure = find_root(
            lower_bound=UnitConstants.STANDARD_PRESSURE_BARA + self.stages[0].pressure_drop_ahead_of_stage,
            upper_bound=upper_bound_for_inlet_pressure if upper_bound_for_inlet_pressure else outlet_pressure,
            func=lambda x: _calculate_train_result_given_rate_ps_speed(_inlet_pressure=x).discharge_pressure
            - outlet_pressure,
        )

        return self.calculate_compressor_train_given_rate_ps_speed(
            speed=speed,
            mass_rate_kg_per_hour=mass_rate_kg_per_hour,
            inlet_pressure_bara=choked_inlet_pressure,
        )

    def calculate_compressor_train_given_rate_ps_pd_speed(
        self,
        speed: float,
        inlet_pressure: float,
        outlet_pressure: float,
        mass_rate_kg_per_hour: float,
    ) -> CompressorTrainResultSingleTimeStep:
        # if full recirculation gives low enough pressure, iterate on asv_rate_fraction to reach the target
        def _calculate_train_result_given_rate_ps_speed_asv_rate_fraction(
            asv_rate_fraction: float,
        ) -> CompressorTrainResultSingleTimeStep:
            """Note that we use outside variables for clarity and to avoid class instances."""
            train_results_this_time_step = self.calculate_compressor_train_given_rate_ps_speed(
                mass_rate_kg_per_hour=mass_rate_kg_per_hour,
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
                mass_rate_kg_per_hour=mass_rate_kg_per_hour,
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
                    mass_rate_kg_per_hour=mass_rate_kg_per_hour,
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
                mass_rate_kg_per_hour=mass_rate_kg_per_hour,
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
                logger.debug(msg)
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
                mass_rate_kg_per_hour=mass_rate_kg_per_hour,
                inlet_pressure_bara=inlet_pressure,
                speed=speed,
                asv_rate_fraction=result_asv_rate_margin,
            )
        # For INDIVIDUAL_ASV_PRESSURE and COMMON_ASV current solution is making a single speed equivalent train
        elif self.pressure_control in (
            FixedSpeedPressureControl.INDIVIDUAL_ASV_PRESSURE,
            FixedSpeedPressureControl.COMMON_ASV,
        ):
            # Run as a single speed train with rate adjustment
            single_speed_train = get_single_speed_equivalent_train(compressor_train=self, speed=speed)
            single_speed_train_results = single_speed_train._evaluate_rate_ps_pd(
                rate=np.asarray(
                    [self.fluid.mass_rate_to_standard_rate(mass_rate_kg_per_hour=np.asarray(mass_rate_kg_per_hour))]
                ),
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


def get_single_speed_equivalent_train(
    compressor_train: VariableSpeedCompressorTrainCommonShaft, speed: float
) -> SingleSpeedCompressorTrainCommonShaft:
    """Create a single speed compressor train equivalent to given variable speed compressor train at a constant speed

    Args:
        compressor_train: A variable speed compressor train
        speed: Shaft speed to keep variable compressor train on

    Returns:
        A single speed compressor train at given shaft speed

    """
    single_speed_compressor_stages = [
        CompressorTrainStage(
            compressor_chart=get_single_speed_equivalent(compressor_chart=stage.compressor_chart, speed=speed),
            inlet_temperature_kelvin=stage.inlet_temperature_kelvin,
            remove_liquid_after_cooling=stage.remove_liquid_after_cooling,
            pressure_drop_ahead_of_stage=stage.pressure_drop_ahead_of_stage,
        )
        for stage in compressor_train.stages
    ]

    return SingleSpeedCompressorTrainCommonShaft(
        data_transfer_object=dto.SingleSpeedCompressorTrain(
            fluid_model=compressor_train.fluid.fluid_model,
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
            pressure_control=compressor_train.pressure_control,
            maximum_discharge_pressure=None,
            energy_usage_adjustment_constant=compressor_train.data_transfer_object.energy_usage_adjustment_constant,
            energy_usage_adjustment_factor=compressor_train.data_transfer_object.energy_usage_adjustment_factor,
        ),
    )
