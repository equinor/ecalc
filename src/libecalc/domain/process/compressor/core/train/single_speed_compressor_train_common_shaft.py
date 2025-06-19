from libecalc.common.errors.exceptions import IllegalStateException
from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl
from libecalc.common.logger import logger
from libecalc.common.units import UnitConstants
from libecalc.domain.process.compressor.core.results import CompressorTrainResultSingleTimeStep
from libecalc.domain.process.compressor.core.train.base import CompressorTrainModel
from libecalc.domain.process.compressor.core.train.train_evaluation_input import CompressorTrainEvaluationInput
from libecalc.domain.process.compressor.core.train.utils.common import EPSILON
from libecalc.domain.process.compressor.core.train.utils.numeric_methods import (
    find_root,
    maximize_x_given_boolean_condition_function,
)
from libecalc.domain.process.compressor.dto import SingleSpeedCompressorTrain
from libecalc.domain.process.entities.fluid_stream import FluidStream


class SingleSpeedCompressorTrainCommonShaft(CompressorTrainModel):
    """
    A model representing a fixed-speed compressor train.

    Compressor Charts:
        The compressor charts must be pre-defined and based on a single fixed speed.

    FluidStream:
        Represents the fluid model. Refer to the FluidStream class for details.

    Pressure Control:
        Defines the mechanism used to achieve the target discharge pressure. The following control options are supported:

        Choking Options:
            - "UPSTREAM_CHOKE": Reduces suction pressure (using an upstream choke valve) to meet the target discharge pressure.
            - "DOWNSTREAM_CHOKE": Reduces discharge pressure to the target value after calculations (using a downstream choke valve).

        Anti-Surge Valve (ASV) Recirculation Options:
            - "INDIVIDUAL_ASV_RATE": Increases the fluid rate (using the ASV for recirculation) to lower the head value, achieving the target outlet pressure.
              For multiple compressor stages, each compressor has its own ASV, and the rate is increased proportionally across all stages:
                actual_rate_after_asv = actual_rate_without_asv +
                                        (compressor_max_actual_rate - actual_rate_without_asv) * asv_fraction
              Here, `asv_fraction` is consistent across all stages.

            - "INDIVIDUAL_ASV_PRESSURE": Ensures the ratio of discharge pressure to suction pressure is equal across all compressors in the train.
              ASVs are independently adjusted to achieve the required discharge pressure for each compressor.

            - "COMMON_ASV": Operates the ASV over the entire train rather than individual compressors.
              The mass rate remains constant across all compressors in the train.

    Maximum Discharge Pressure:
        This is an optional setting, supported only for "DOWNSTREAM_CHOKE" pressure control.
        By default, the discharge pressure is unlimited. However, for safety reasons, a maximum discharge pressure can be specified.
        If the calculated discharge pressure exceeds this limit, the system switches to "UPSTREAM_CHOKE" control,
        setting the discharge pressure to the specified maximum.

    Configuration:
        - Each stage requires a pre-defined (single/fixed speed) compressor chart, an inlet temperature, and an option to remove liquids after compression and cooling.
        - The pressure drop from the previous stage must also be specified (can be 0).
        - The compressor train is evaluated using a single inlet for the entire train (fluid specification and rate).
    """

    def __init__(
        self,
        data_transfer_object: SingleSpeedCompressorTrain,
    ):
        logger.debug(
            f"Creating SingleSpeedCompressorTrainCommonShaft with n_stages: {len(data_transfer_object.stages)}"
        )
        super().__init__(data_transfer_object)
        self.data_transfer_object = data_transfer_object

    @property
    def pressure_control(self) -> FixedSpeedPressureControl:
        return self.data_transfer_object.pressure_control

    @property
    def maximum_discharge_pressure(self) -> float:
        return self.data_transfer_object.maximum_discharge_pressure

    def evaluate_given_fluid_streams_and_constraints(
        self,
        fluid_streams: list[FluidStream],
        constraints: CompressorTrainEvaluationInput,
    ) -> CompressorTrainResultSingleTimeStep:
        """
        Evaluate a single-speed compressor train total power given a fluid stream and constraints for the evaluation
        as input. The pressure control will be invoked to reach the target discharge pressure.

        The evaluation varies depending on the chosen pressure control mechanism.

        For some inputs the point may fall outside the capacity of one or more compressor stages. In such cases,
        a `failure_status` describing the issue will be included in the `CompressorTrainResult`.

        In certain scenarios, a feasible solution may not exist. For example, the target discharge pressure may
        be too high or too low given the rate and suction pressure. In these cases, calculations are still performed,
        and a result is returned with a `failure_status` indicating whether the target discharge pressure is too high
        or too low. The returned result will include either:
            - No ASV recirculation (if the target pressure is too high, returning results with the maximum possible
              discharge pressure).
            - Maximum recirculation (if the target pressure is too low, returning results with the lowest possible
              discharge pressure).

        Args:
            fluid_streams (list[FluidStream]): A list of fluid streams to evaluate. Only a single fluid stream is supported.
            constraints (CompressorTrainEvaluationInput): The constraints for the evaluation, including discharge pressure.

        Returns:
            CompressorTrainResultSingleTimeStep: The result of the evaluation for a single time step, including power,
            pressure, and failure status if applicable.
        """
        # Ensure only one fluid stream is provided; raise an exception otherwise.
        if len(fluid_streams) > 1:
            raise IllegalStateException("SingleSpeedCompressorTrain does not support multiple fluid streams.")

        # Extract the inlet stream from the provided fluid streams.
        train_inlet_stream = fluid_streams[0]

        # Check if the discharge pressure exceeds the maximum allowed discharge pressure.
        if self.maximum_discharge_pressure is not None:
            if (
                constraints.discharge_pressure is not None
                and constraints.discharge_pressure > self.maximum_discharge_pressure
            ):
                raise ValueError(
                    f"Discharge pressure in input data ({constraints.discharge_pressure}) is "
                    f"larger than maximum allowed discharge pressure in single speed compressor model"
                    f" ({self.maximum_discharge_pressure})"
                )

        # If the inlet stream has a positive mass rate, evaluate using pressure control.
        if train_inlet_stream.mass_rate > 0:
            train_result = self.evaluate_with_pressure_control_given_fluid_streams_and_constraints(
                fluid_streams=fluid_streams,
                constraints=constraints,
            )
        else:
            # If the mass rate is zero or negative, return an empty result for the compressor train.
            train_result = CompressorTrainResultSingleTimeStep.create_empty(number_of_stages=len(self.stages))

        # Return the evaluation result.
        return train_result

    def calculate_compressor_train(
        self,
        fluid_streams: list[FluidStream],
        constraints: CompressorTrainEvaluationInput,
        asv_rate_fraction: float = 0.0,
        asv_additional_mass_rate: float = 0.0,
    ) -> CompressorTrainResultSingleTimeStep:
        """
        Model of a single-speed compressor train where the Anti-Surge Valve (ASV) is only used below the minimum flow,
        and the outlet pressure is determined by the requested rate.

        Args:
            fluid_streams (list[FluidStream]): A list of fluid streams to evaluate. Only a single fluid stream is supported.
            constraints (CompressorTrainEvaluationInput): The constraints for the evaluation, including discharge pressure.
            asv_rate_fraction (float, optional): The fraction of the ASV rate to apply. Defaults to 0.0.
            asv_additional_mass_rate (float, optional): Additional mass rate to apply via the ASV. Defaults to 0.0.

        Returns:
            CompressorTrainResultSingleTimeStep: The result of the evaluation for a single time step, including inlet and
            outlet streams, stage results, and whether the power exceeds the maximum allowed.
        """
        # Ensure only one fluid stream is provided; raise an exception otherwise.
        if len(fluid_streams) > 1:
            raise IllegalStateException("SingleSpeedCompressorTrain does not support multiple fluid streams.")

        # Extract the inlet stream from the provided fluid streams.
        previous_stage_outlet_stream = train_inlet_stream = fluid_streams[0]

        # Initialize the list to store results for each stage and set the initial outlet stream.
        stage_results = []

        # Iterate through each stage in the compressor train.
        for stage in self.stages:
            # Evaluate the current stage with the given inlet stream and ASV parameters.
            stage_results.append(
                stage.evaluate(
                    inlet_stream_stage=previous_stage_outlet_stream,
                    asv_rate_fraction=asv_rate_fraction,
                    asv_additional_mass_rate=asv_additional_mass_rate,
                )
            )
            # Set the inlet stream to the next stage to be the last stage's outlet stream.
            previous_stage_outlet_stream = stage_results[-1].outlet_stream

        # Check if the target pressures are met based on the constraints and stage results.
        target_pressure_status = self.check_target_pressures(
            constraints=constraints,
            results=stage_results,
        )

        # Return the result of the compressor train evaluation, including all relevant data.
        return CompressorTrainResultSingleTimeStep(
            inlet_stream=train_inlet_stream,
            outlet_stream=previous_stage_outlet_stream,
            speed=float("nan"),  # Speed is not applicable for a single-speed compressor train.
            stage_results=stage_results,
            above_maximum_power=sum([stage_result.power_megawatt for stage_result in stage_results])
            > self.maximum_power
            if self.maximum_power
            else False,  # Check if the total power exceeds the maximum allowed power.
            target_pressure_status=target_pressure_status,  # Status of whether the target pressures are met.
        )

    def _get_max_std_rate_single_timestep(
        self,
        fluid_streams: list[FluidStream],
        constraints: CompressorTrainEvaluationInput,
        allow_asv: bool = False,
    ) -> float:
        """
        Calculate the maximum mass rate [kg/hour] that the compressor train can operate at for a single time step.

        Args:
            fluid_streams (list[FluidStream]): List of fluid streams (only one is supported).
            constraints (CompressorTrainEvaluationInput): Evaluation constraints.
            allow_asv (bool): If True, allows ASV recirculation below the minimum mass rate.

        Returns:
            float: Maximum mass rate in kg/hour, or 0 if no valid solution exists.
        """
        if len(fluid_streams) > 1:
            raise IllegalStateException("Only one fluid stream is supported.")
        target_discharge_pressure = constraints.discharge_pressure
        if target_discharge_pressure is None:
            raise ValueError("Discharge pressure must be specified in constraints.")
        inlet_stream = fluid_streams[0]
        inlet_density = inlet_stream.density

        def _calculate_train_result(mass_rate: float) -> CompressorTrainResultSingleTimeStep:
            return self.calculate_compressor_train(
                fluid_streams=[FluidStream(inlet_stream.thermo_system, mass_rate)],
                constraints=CompressorTrainEvaluationInput(
                    discharge_pressure=target_discharge_pressure,
                    speed=constraints.speed,
                ),
            )

        min_rate = self.stages[0].compressor_chart.minimum_rate * inlet_density
        max_rate = self.stages[0].compressor_chart.maximum_rate * inlet_density

        min_result = _calculate_train_result(min_rate)
        max_result = _calculate_train_result(max_rate)

        if not min_result.within_capacity:
            if allow_asv and _calculate_train_result(EPSILON).within_capacity:
                min_rate = EPSILON
                max_rate = maximize_x_given_boolean_condition_function(
                    x_min=EPSILON,
                    x_max=min_rate,
                    bool_func=lambda x: _calculate_train_result(x).within_capacity,
                    convergence_tolerance=1e-3,
                    maximum_number_of_iterations=20,
                )
            else:
                return 0.0

        if not max_result.within_capacity:
            max_rate = maximize_x_given_boolean_condition_function(
                x_min=min_rate,
                x_max=max_rate,
                bool_func=lambda x: _calculate_train_result(x).within_capacity,
                convergence_tolerance=1e-3,
                maximum_number_of_iterations=20,
            )

            if min_result.discharge_pressure < target_discharge_pressure:
                return 0.0
            if target_discharge_pressure >= max_result.discharge_pressure:
                result_rate = find_root(
                    lower_bound=min_rate,
                    upper_bound=max_rate,
                    func=lambda x: _calculate_train_result(x).discharge_pressure - target_discharge_pressure,
                    relative_convergence_tolerance=1e-3,
                    maximum_number_of_iterations=20,
                )
                return (
                    self._check_maximum_rate_against_maximum_power(
                        maximum_mass_rate=_calculate_train_result(result_rate).mass_rate_kg_per_hour,
                        inlet_stream=inlet_stream,
                        discharge_pressure=target_discharge_pressure,
                    )
                    / inlet_stream.standard_density_gas_phase_after_flash
                    * UnitConstants.HOURS_PER_DAY
                )

        if self.data_transfer_object.pressure_control == FixedSpeedPressureControl.DOWNSTREAM_CHOKE:
            if self.evaluate_given_fluid_streams_and_constraints(
                fluid_streams=[FluidStream(inlet_stream.thermo_system, max_rate)],
                constraints=constraints,
            ).is_valid:
                return (
                    self._check_maximum_rate_against_maximum_power(
                        maximum_mass_rate=max_rate,
                        inlet_stream=inlet_stream,
                        discharge_pressure=target_discharge_pressure,
                    )
                    / inlet_stream.standard_density_gas_phase_after_flash
                    * UnitConstants.HOURS_PER_DAY
                )

        if self.data_transfer_object.pressure_control == FixedSpeedPressureControl.UPSTREAM_CHOKE:
            max_rate = maximize_x_given_boolean_condition_function(
                x_min=min_rate,
                x_max=max_rate,
                bool_func=lambda x: _calculate_train_result(x).within_capacity,
                convergence_tolerance=1e-3,
                maximum_number_of_iterations=20,
            )
            return (
                self._check_maximum_rate_against_maximum_power(
                    maximum_mass_rate=max_rate,
                    inlet_stream=inlet_stream,
                    discharge_pressure=target_discharge_pressure,
                )
                / inlet_stream.standard_density_gas_phase_after_flash
                * UnitConstants.HOURS_PER_DAY
            )

        return 0.0

    def _check_maximum_rate_against_maximum_power(
        self, inlet_stream: FluidStream, maximum_mass_rate: float, discharge_pressure: float
    ) -> float:
        """Check if the maximum_rate, suction and discharge pressure power requirement exceeds a potential maximum power

        Args:
            maximum_mass_rate:  Found maximum mass rate for the train (at given suction and discharge pressure)
            inlet_stream: Train inlet fluid stream
            discharge_pressure: Discharge pressure for the train

        Returns:
            Maximum rate constrained by maximum power (set to 0 if required power > maximum power)
        """
        if self.data_transfer_object.maximum_power:
            new_inlet_stream = [
                FluidStream(
                    thermo_system=inlet_stream.thermo_system,
                    mass_rate=maximum_mass_rate,
                )
            ]
            if (
                self.evaluate_given_fluid_streams_and_constraints(
                    fluid_streams=new_inlet_stream,
                    constraints=CompressorTrainEvaluationInput(
                        discharge_pressure=discharge_pressure,
                    ),
                ).power_megawatt
                > self.data_transfer_object.maximum_power
            ):
                return 0.0

        return maximum_mass_rate
