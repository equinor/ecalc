from libecalc.common.errors.exceptions import EcalcError, IllegalStateException
from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl
from libecalc.common.fluid import FluidStream as FluidStreamDTO
from libecalc.common.logger import logger
from libecalc.domain.process.chart.chart_area_flag import ChartAreaFlag
from libecalc.domain.process.compressor.core.results import (
    CompressorTrainResultSingleTimeStep,
)
from libecalc.domain.process.compressor.core.train.base import CompressorTrainModel
from libecalc.domain.process.compressor.core.train.fluid import FluidStream
from libecalc.domain.process.compressor.core.train.utils.common import (
    EPSILON,
    PRESSURE_CALCULATION_TOLERANCE,
)
from libecalc.domain.process.compressor.core.train.utils.numeric_methods import (
    find_root,
    maximize_x_given_boolean_condition_function,
)
from libecalc.domain.process.compressor.dto import SingleSpeedCompressorTrain
from libecalc.domain.process.core.results.compressor import TargetPressureStatus


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

    def _evaluate_rate_ps_pd(
        self,
        rate: float,
        suction_pressure: float,
        discharge_pressure: float,
    ) -> CompressorTrainResultSingleTimeStep:
        """
        Evaluate a single-speed compressor train total power given rate, suction pressure, and discharge pressure.

        The evaluation varies depending on the chosen pressure control mechanism.

        For some inputs (rate, suction pressure, and discharge pressure), the point may fall outside the capacity
        of one or more compressor stages. In such cases, a `failure_status` describing the issue will be included
        in the `CompressorTrainResult`.

        In certain scenarios, a feasible solution may not exist. For example, the target discharge pressure may
        be too high or too low given the rate and suction pressure. In these cases, calculations are still performed,
        and a result is returned with a `failure_status` indicating whether the target discharge pressure is too high
        or too low. The returned result will include either:
            - No ASV recirculation (if the target pressure is too high, returning results with the maximum possible
              discharge pressure).
            - Maximum recirculation (if the target pressure is too low, returning results with the lowest possible
              discharge pressure).

        Args:
            rate (float): Standard volume rate in [Sm3/day].
            suction_pressure (float): Suction pressure per time step in [bara].
            discharge_pressure (float): Discharge pressure per time step in [bara].

        Returns:
            CompressorTrainResultSingleTimeStep: The result of the evaluation for a single time step.
        """
        if self.maximum_discharge_pressure is not None:
            if discharge_pressure > self.maximum_discharge_pressure:
                raise ValueError(
                    f"Dishcarge pressure in input data ({discharge_pressure}) is "
                    f"larger than maximum allowed discharge pressure in single speed compressor model"
                    f" ({self.maximum_discharge_pressure})"
                )
        mass_rate_kg_per_hour = self.fluid.standard_rate_to_mass_rate(standard_rates=rate)

        if mass_rate_kg_per_hour > 0:
            self.target_suction_pressure = suction_pressure
            self.target_discharge_pressure = discharge_pressure
            if self.pressure_control == FixedSpeedPressureControl.DOWNSTREAM_CHOKE:
                train_result = self._evaluate_train_result_downstream_choking(
                    mass_rate_kg_per_hour=mass_rate_kg_per_hour,
                    suction_pressure=suction_pressure,
                    discharge_pressure=discharge_pressure,
                )
            elif self.pressure_control == FixedSpeedPressureControl.UPSTREAM_CHOKE:
                train_result = self._evaluate_train_results_upstream_choking(
                    mass_rate_kg_per_hour=mass_rate_kg_per_hour,
                    suction_pressure=suction_pressure,
                    discharge_pressure=discharge_pressure,
                )
            elif self.pressure_control == FixedSpeedPressureControl.INDIVIDUAL_ASV_RATE:
                train_result = self._evaluate_train_result_individual_asv_rate(
                    mass_rate_kg_per_hour=mass_rate_kg_per_hour,
                    suction_pressure=suction_pressure,
                    discharge_pressure=discharge_pressure,
                )
            elif self.pressure_control == FixedSpeedPressureControl.INDIVIDUAL_ASV_PRESSURE:
                train_result = self._evaluate_train_result_asv_pressure(
                    mass_rate_kg_per_hour=mass_rate_kg_per_hour,
                    suction_pressure=suction_pressure,
                    discharge_pressure=discharge_pressure,
                )
            elif self.pressure_control == FixedSpeedPressureControl.COMMON_ASV:
                train_result = self._evaluate_train_result_common_asv(
                    mass_rate_kg_per_hour=mass_rate_kg_per_hour,
                    suction_pressure=suction_pressure,
                    discharge_pressure=discharge_pressure,
                )
            else:
                raise ValueError(f"Pressure control {self.pressure_control} not supported")
        else:
            train_result = CompressorTrainResultSingleTimeStep.create_empty(number_of_stages=len(self.stages))

        return train_result

    def _evaluate_train_result_downstream_choking(
        self,
        mass_rate_kg_per_hour: float,
        suction_pressure: float,
        discharge_pressure: float,
    ) -> CompressorTrainResultSingleTimeStep:
        """
        Evaluate a single-speed compressor train's total power given mass rate, suction pressure, and discharge pressure.

        This method assumes that the discharge pressure is controlled to meet the target using a downstream choke valve.

        Args:
            mass_rate_kg_per_hour (float): Mass rate in kilograms per hour [kg/hour].
            suction_pressure (float): Suction pressure per time step in bar absolute [bara].
            discharge_pressure (float): Discharge pressure per time step in bar absolute [bara].

        Returns:
            CompressorTrainResultSingleTimeStep: The result of the evaluation for a single time step.
        """
        train_result = self._evaluate_rate_ps(
            mass_rate_kg_per_hour=mass_rate_kg_per_hour,
            inlet_pressure_train_bara=suction_pressure,
        )

        if self.maximum_discharge_pressure is not None:
            if train_result.discharge_pressure * (1 + PRESSURE_CALCULATION_TOLERANCE) > self.maximum_discharge_pressure:
                new_train_result = self._evaluate_rate_pd(
                    mass_rate_kg_per_hour=mass_rate_kg_per_hour,
                    outlet_pressure_train_bara=self.maximum_discharge_pressure,
                )
                train_result.stage_results = new_train_result.stage_results
                train_result.outlet_stream = new_train_result.outlet_stream
                train_result.target_pressure_status = self.check_target_pressures(
                    calculated_suction_pressure=train_result.inlet_stream.pressure_bara,
                    calculated_discharge_pressure=train_result.outlet_stream.pressure_bara,
                )

        if train_result.target_pressure_status == TargetPressureStatus.ABOVE_TARGET_DISCHARGE_PRESSURE:
            new_outlet_stream = FluidStream(
                fluid_model=train_result.outlet_stream,
                pressure_bara=discharge_pressure,
                temperature_kelvin=train_result.outlet_stream.temperature_kelvin,
            )
            train_result.outlet_stream = FluidStreamDTO.from_fluid_domain_object(fluid_stream=new_outlet_stream)
            train_result.target_pressure_status = self.check_target_pressures(
                calculated_suction_pressure=train_result.inlet_stream.pressure_bara,
                calculated_discharge_pressure=train_result.outlet_stream.pressure_bara,
            )

        return train_result

    def _evaluate_train_results_upstream_choking(
        self,
        mass_rate_kg_per_hour: float,
        suction_pressure: float,
        discharge_pressure: float,
    ) -> CompressorTrainResultSingleTimeStep:
        """
        Evaluate the compressor train's total power assuming upstream choking is used to control suction pressure.

        This method iteratively adjusts the suction pressure to achieve the target discharge pressure.

        Args:
            mass_rate_kg_per_hour (float): Mass rate in kilograms per hour [kg/hour].
            suction_pressure (float): Suction pressure per time step in bar absolute [bara].
            discharge_pressure (float): Discharge pressure per time step in bar absolute [bara].

        Returns:
            CompressorTrainResultSingleTimeStep: The result of the evaluation for a single time step.
        """
        train_result = self._evaluate_rate_pd(
            mass_rate_kg_per_hour=mass_rate_kg_per_hour,
            outlet_pressure_train_bara=discharge_pressure,
        )

        if train_result.target_pressure_status == TargetPressureStatus.BELOW_TARGET_SUCTION_PRESSURE:
            new_inlet_stream = FluidStream(
                fluid_model=train_result.inlet_stream,
                pressure_bara=suction_pressure,
                temperature_kelvin=train_result.inlet_stream.temperature_kelvin,
            )
            train_result.inlet_stream = FluidStreamDTO.from_fluid_domain_object(fluid_stream=new_inlet_stream)
            train_result.target_pressure_status = self.check_target_pressures(
                calculated_suction_pressure=train_result.inlet_stream.pressure_bara,
                calculated_discharge_pressure=train_result.outlet_stream.pressure_bara,
            )

        return train_result

    def _evaluate_train_result_individual_asv_rate(
        self,
        mass_rate_kg_per_hour: float,
        suction_pressure: float,
        discharge_pressure: float,
    ) -> CompressorTrainResultSingleTimeStep:
        """
        Evaluate the compressor train's total power using individual ASV rate control.

        This method increases the fluid rate using the ASV to lower the head value and achieve the target discharge pressure.
        The recirculation is distributed proportionally across all compressor stages.

        Args:
            mass_rate_kg_per_hour (float): Mass rate in kilograms per hour [kg/hour].
            suction_pressure (float): Suction pressure per time step in bar absolute [bara].
            discharge_pressure (float): Discharge pressure per time step in bar absolute [bara].

        Returns:
            CompressorTrainResultSingleTimeStep: The result of the evaluation for a single time step.
        """
        return self._evaluate_ps_pd_minimum_mass_rate(
            inlet_pressure_train_bara=suction_pressure,
            outlet_pressure_train_bara=discharge_pressure,
            minimum_mass_rate_kg_per_hour=mass_rate_kg_per_hour,
        )

    def _evaluate_train_result_asv_pressure(
        self,
        mass_rate_kg_per_hour: float,
        suction_pressure: float,
        discharge_pressure: float,
    ) -> CompressorTrainResultSingleTimeStep:
        """
        Evaluate the compressor train's total power using individual ASV pressure control.

        This method ensures that the pressure ratio (discharge pressure / suction pressure) is equal across all compressors
        in the train. ASVs are independently adjusted to achieve the required discharge pressure for each compressor.

        Args:
            mass_rate_kg_per_hour (float): Mass rate in kilograms per hour [kg/hour].
            suction_pressure (float): Suction pressure per time step in bar absolute [bara].
            discharge_pressure (float): Discharge pressure per time step in bar absolute [bara].

        Returns:
            CompressorTrainResultSingleTimeStep: The result of the evaluation for a single time step.
        """
        inlet_stream_train = self.fluid.get_fluid_stream(
            pressure_bara=suction_pressure,
            temperature_kelvin=self.stages[0].inlet_temperature_kelvin,
        )
        pressure_ratio_per_stage = self.calculate_pressure_ratios_per_stage(
            suction_pressure=suction_pressure,
            discharge_pressure=discharge_pressure,
        )
        inlet_stream_stage = outlet_stream_stage = inlet_stream_train
        stage_results = []
        for stage in self.stages:
            outlet_pressure_for_stage = inlet_stream_stage.pressure_bara * pressure_ratio_per_stage
            stage_result = stage.evaluate_given_speed_and_target_discharge_pressure(
                target_discharge_pressure=outlet_pressure_for_stage,
                mass_rate_kg_per_hour=mass_rate_kg_per_hour,
                inlet_stream_stage=inlet_stream_stage,
            )
            outlet_stream_stage = inlet_stream_stage.set_new_pressure_and_temperature(
                new_pressure_bara=stage_result.outlet_stream.pressure_bara,
                new_temperature_kelvin=stage_result.outlet_stream.temperature_kelvin,
            )
            inlet_stream_stage = outlet_stream_stage
            stage_results.append(stage_result)

        # check if target pressures are met
        target_pressure_status = self.check_target_pressures(
            calculated_suction_pressure=inlet_stream_train.pressure_bara,
            calculated_discharge_pressure=stage_results[-1].outlet_stream.pressure_bara,
        )
        return CompressorTrainResultSingleTimeStep(
            inlet_stream=FluidStreamDTO.from_fluid_domain_object(fluid_stream=inlet_stream_train),
            outlet_stream=FluidStreamDTO.from_fluid_domain_object(fluid_stream=outlet_stream_stage),
            speed=float("nan"),
            stage_results=stage_results,
            target_pressure_status=target_pressure_status,
        )

    def _evaluate_train_result_common_asv(
        self,
        mass_rate_kg_per_hour: float,
        suction_pressure: float,
        discharge_pressure: float,
    ) -> CompressorTrainResultSingleTimeStep:
        """
        Evaluate the compressor train's total power using common ASV control.

        This method uses a single ASV for the entire train, ensuring the same mass rate passes through all compressors.
        The ASV increases the net rate until the head is reduced enough to meet the target discharge pressure.

        Args:
            mass_rate_kg_per_hour (float): Mass rate in kilograms per hour [kg/hour].
            suction_pressure (float): Suction pressure per time step in bar absolute [bara].
            discharge_pressure (float): Discharge pressure per time step in bar absolute [bara].

        Returns:
            CompressorTrainResultSingleTimeStep: The result of the evaluation for a single time step.
        """
        train_result = self._evaluate_ps_pd_constant_mass_rate(
            inlet_pressure_train_bara=suction_pressure,
            outlet_pressure_train_bara=discharge_pressure,
            minimum_mass_rate_kg_per_hour=mass_rate_kg_per_hour,
        )

        return train_result

    def _evaluate_rate_ps(
        self,
        mass_rate_kg_per_hour: float,
        inlet_pressure_train_bara: float,
    ) -> CompressorTrainResultSingleTimeStep:
        """Evaluate the single speed compressor train total power given mass rate and suction pressure. The discharge
        pressure is a result of the inlet conditions, fluid rate and the resulting process.

        Args:
            mass_rate_kg_per_hour (float): Mass rate [kg/hour].
            inlet_pressure_train_bara (float): Inlet pressure per time step [bara].

        Returns:
            CompressorTrainResultSingleTimeStep: The result of the evaluation for a single time step.
        """
        mass_rate_for_stages = self.number_of_compressor_stages * [mass_rate_kg_per_hour]
        train_inlet_stream = self.fluid.get_fluid_stream(
            pressure_bara=inlet_pressure_train_bara,
            temperature_kelvin=self.stages[0].inlet_temperature_kelvin,
        )
        return self.calculate_single_speed_train(
            train_inlet_stream=train_inlet_stream,
            mass_rate_kg_per_hour_per_stage=mass_rate_for_stages,
        )

    def _evaluate_rate_pd(
        self,
        mass_rate_kg_per_hour: float,
        outlet_pressure_train_bara: float,
    ) -> CompressorTrainResultSingleTimeStep:
        """Evaluate a single speed compressor train total power given mass rates and outlet pressures (one per time step).
        Newton iteration is used on the forward model which flashes the fluid at each stage given the inlet conditions to
        find the suction pressure that results in the target discharge pressure.

        Args:
            mass_rate_kg_per_hour (float): Mass rate [kg/hour].
            outlet_pressure_train_bara (float): Discharge pressure per time step [bara].

        Returns:
            CompressorTrainResultSingleTimeStep: The result of the evaluation for a single time step.
        """
        mass_rate_for_stages = self.number_of_compressor_stages * [mass_rate_kg_per_hour]

        # As the inlet stream depends on the inlet pressure,
        # iterate on the inlet pressure to meet requested discharge pressure
        def _calculate_train_result_given_inlet_pressure(
            inlet_pressure: float,
        ) -> CompressorTrainResultSingleTimeStep:
            """Note that we use outside variables for clarity and to avoid class instances."""
            train_inlet_stream = self.fluid.get_fluid_stream(
                pressure_bara=inlet_pressure,
                temperature_kelvin=self.stages[0].inlet_temperature_kelvin,
            )
            return self.calculate_single_speed_train(
                train_inlet_stream=train_inlet_stream,
                mass_rate_kg_per_hour_per_stage=mass_rate_for_stages,
            )

        result_inlet_pressure = find_root(
            lower_bound=EPSILON + self.stages[0].pressure_drop_ahead_of_stage,
            upper_bound=outlet_pressure_train_bara,
            func=lambda x: _calculate_train_result_given_inlet_pressure(inlet_pressure=x).discharge_pressure
            - outlet_pressure_train_bara,
        )

        return _calculate_train_result_given_inlet_pressure(inlet_pressure=result_inlet_pressure)

    def _evaluate_ps_pd_minimum_mass_rate(
        self,
        inlet_pressure_train_bara: float,
        outlet_pressure_train_bara: float,
        minimum_mass_rate_kg_per_hour: float,
    ) -> CompressorTrainResultSingleTimeStep:
        """
        Evaluate the total power of a single-speed compressor train given suction pressure, discharge pressure,
        and a minimum mass rate.

        This method assumes that the discharge pressure is controlled to meet the target using anti-surge valves (ASVs).
        The ASVs increase the net rate until the head is reduced enough in each compressor stage to meet the target
        discharge pressure. For multiple compressor stages, the ASV recirculation is distributed proportionally across
        all stages, ensuring the same ASV fraction is applied to each stage.

        A Newton iteration is used to find the ASV fraction that results in the target discharge pressure.

        Args:
            inlet_pressure_train_bara (float): Suction pressure per time step in bar absolute [bara].
            outlet_pressure_train_bara (float): Discharge pressure per time step in bar absolute [bara].
            minimum_mass_rate_kg_per_hour (float): Minimum gross mass rate for each stage in kilograms per hour [kg/hour].

        Returns:
            CompressorTrainResultSingleTimeStep: The result of the evaluation for a single time step.
        """
        # Iterate on rate until pressures are met
        train_inlet_stream = self.fluid.get_fluid_stream(
            pressure_bara=inlet_pressure_train_bara,
            temperature_kelvin=self.stages[0].inlet_temperature_kelvin,
        )

        def _calculate_train_result_given_asv_rate_margin(
            asv_rate_fraction: float,
        ) -> CompressorTrainResultSingleTimeStep:
            """Note that we use outside variables for clarity and to avoid class instances."""
            return self.calculate_single_speed_train(
                train_inlet_stream=train_inlet_stream,
                mass_rate_kg_per_hour_per_stage=[minimum_mass_rate_kg_per_hour] * self.number_of_compressor_stages,
                asv_rate_fraction=asv_rate_fraction,
            )

        minimum_asv_fraction = 0.0
        maximum_asv_fraction = 1.0
        train_result_for_minimum_asv_rate_fraction = _calculate_train_result_given_asv_rate_margin(
            asv_rate_fraction=minimum_asv_fraction
        )
        if (train_result_for_minimum_asv_rate_fraction.chart_area_status == ChartAreaFlag.ABOVE_MAXIMUM_FLOW_RATE) or (
            outlet_pressure_train_bara > train_result_for_minimum_asv_rate_fraction.discharge_pressure
        ):
            return train_result_for_minimum_asv_rate_fraction
        train_result_for_maximum_asv_rate_fraction = _calculate_train_result_given_asv_rate_margin(
            asv_rate_fraction=maximum_asv_fraction
        )
        if outlet_pressure_train_bara < train_result_for_maximum_asv_rate_fraction.discharge_pressure:
            return train_result_for_maximum_asv_rate_fraction

        result_asv_rate_margin = find_root(
            lower_bound=0.0,
            upper_bound=1.0,
            func=lambda x: _calculate_train_result_given_asv_rate_margin(asv_rate_fraction=x).discharge_pressure
            - outlet_pressure_train_bara,
        )
        # This mass rate, is the mass rate to use as mass rate after asv for each stage,
        # thus the asv in each stage should be set to correspond to this mass rate
        return _calculate_train_result_given_asv_rate_margin(asv_rate_fraction=result_asv_rate_margin)

    def _evaluate_ps_pd_constant_mass_rate(
        self,
        inlet_pressure_train_bara: float,
        outlet_pressure_train_bara: float,
        minimum_mass_rate_kg_per_hour: float,
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
            inlet_pressure_train_bara (float): Suction pressure per time step in bar absolute [bara].
            outlet_pressure_train_bara (float): Discharge pressure per time step in bar absolute [bara].
            minimum_mass_rate_kg_per_hour (float): Minimum gross mass rate for each stage in kilograms per hour [kg/hour].

        Returns:
            CompressorTrainResultSingleTimeStep: The result of the evaluation for a single time step.
        """
        # Iterate on rate until pressures are met
        train_inlet_stream = self.fluid.get_fluid_stream(
            pressure_bara=inlet_pressure_train_bara,
            temperature_kelvin=self.stages[0].inlet_temperature_kelvin,
        )

        def _calculate_train_result_given_mass_rate(
            mass_rate_kg_per_hour: float,
        ) -> CompressorTrainResultSingleTimeStep:
            return self.calculate_single_speed_train(
                train_inlet_stream=train_inlet_stream,
                mass_rate_kg_per_hour_per_stage=[mass_rate_kg_per_hour] * self.number_of_compressor_stages,
            )

        def _calculate_train_result_given_additional_mass_rate(
            additional_mass_rate_kg_per_hour: float,
        ) -> CompressorTrainResultSingleTimeStep:
            return self.calculate_single_speed_train(
                train_inlet_stream=train_inlet_stream,
                mass_rate_kg_per_hour_per_stage=[minimum_mass_rate_kg_per_hour] * self.number_of_compressor_stages,
                asv_additional_mass_rate=additional_mass_rate_kg_per_hour,
                target_discharge_pressure=outlet_pressure_train_bara,
            )

        # outer bounds for minimum and maximum mass rate without individual recirculation on stages will be the
        # minimum and maximum mass rate for the first stage, adjusted for the volume entering the first stage
        minimum_mass_rate = max(
            minimum_mass_rate_kg_per_hour,
            self.stages[0].compressor_chart.minimum_rate * train_inlet_stream.density,
        )
        maximum_mass_rate = self.stages[0].compressor_chart.maximum_rate * train_inlet_stream.density

        # if the minimum_mass_rate_kg_per_hour(i.e. before increasing rate with recirculation to lower pressure)
        # is already larger than the maximum mass rate, there is no need for optimization - just add result
        # with minimum_mass_rate_kg_per_hour (which will fail with above maximum flow rate)
        if minimum_mass_rate_kg_per_hour > maximum_mass_rate:
            return _calculate_train_result_given_mass_rate(mass_rate_kg_per_hour=minimum_mass_rate_kg_per_hour)

        train_result_for_minimum_mass_rate = _calculate_train_result_given_mass_rate(
            mass_rate_kg_per_hour=minimum_mass_rate
        )
        train_result_for_maximum_mass_rate = _calculate_train_result_given_mass_rate(
            mass_rate_kg_per_hour=maximum_mass_rate
        )
        if train_result_for_minimum_mass_rate.mass_rate_asv_corrected_is_constant_for_stages:
            if not train_result_for_maximum_mass_rate.mass_rate_asv_corrected_is_constant_for_stages:
                # find the maximum additional_mass_rate that gives train_results.is_valid
                maximum_mass_rate = maximize_x_given_boolean_condition_function(
                    x_min=0.0,  # Searching between near zero and the invalid mass rate above.
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
                x_min=-maximum_mass_rate,  # Searching between near zero and the invalid mass rate above.
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
                x_min=-(
                    minimum_mass_rate + inc * (maximum_mass_rate - minimum_mass_rate)
                ),  # Searching between near zero and the invalid mass rate above.
                x_max=-minimum_mass_rate,
                bool_func=lambda x: _calculate_train_result_given_mass_rate(
                    mass_rate_kg_per_hour=-x
                ).mass_rate_asv_corrected_is_constant_for_stages,
                convergence_tolerance=1e-3,
                maximum_number_of_iterations=20,
            )
            maximum_mass_rate = maximize_x_given_boolean_condition_function(
                x_min=(
                    minimum_mass_rate + inc * (maximum_mass_rate - minimum_mass_rate)
                ),  # Searching between near zero and the invalid mass rate above.
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
        if outlet_pressure_train_bara > train_result_for_minimum_mass_rate.discharge_pressure:
            # will never reach target pressure, too high
            return train_result_for_minimum_mass_rate
        if outlet_pressure_train_bara < train_result_for_maximum_mass_rate.discharge_pressure:
            # will never reach target pressure, too low
            return train_result_for_maximum_mass_rate

        result_mass_rate = find_root(
            lower_bound=minimum_mass_rate,
            upper_bound=maximum_mass_rate,
            func=lambda x: _calculate_train_result_given_mass_rate(mass_rate_kg_per_hour=x).discharge_pressure
            - outlet_pressure_train_bara,
        )
        # This mass rate is the mass rate to use as mass rate after asv for each stage,
        # thus the asv in each stage should be set to correspond to this mass rate
        return _calculate_train_result_given_additional_mass_rate(
            additional_mass_rate_kg_per_hour=result_mass_rate - minimum_mass_rate_kg_per_hour
        )

    def calculate_single_speed_train(
        self,
        train_inlet_stream: FluidStream,
        mass_rate_kg_per_hour_per_stage: list[float],
        asv_rate_fraction: float = 0.0,
        asv_additional_mass_rate: float = 0.0,
        target_discharge_pressure: float | None = None,
    ) -> CompressorTrainResultSingleTimeStep:
        """Model of single speed compressor train where asv is only used below minimum flow, and the outlet pressure is a
        result of the requested rate.

        CompressorTrainResultSingleTimeStep: The result of the evaluation for a single time step.
        """
        stage_results = []
        outlet_stream = train_inlet_stream

        for stage, mass_rate_kg_per_hour in zip(self.stages, mass_rate_kg_per_hour_per_stage):
            inlet_stream = outlet_stream
            stage_result = stage.evaluate(
                inlet_stream_stage=inlet_stream,
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

        # check if target pressures are met
        target_pressure_status = self.check_target_pressures(
            calculated_suction_pressure=train_inlet_stream.pressure_bara,
            calculated_discharge_pressure=outlet_stream.pressure_bara,
        )

        return CompressorTrainResultSingleTimeStep(
            inlet_stream=FluidStreamDTO.from_fluid_domain_object(fluid_stream=train_inlet_stream),
            outlet_stream=FluidStreamDTO.from_fluid_domain_object(fluid_stream=outlet_stream),
            speed=float("nan"),
            stage_results=stage_results,
            above_maximum_power=sum([stage_result.power_megawatt for stage_result in stage_results])
            > self.maximum_power
            if self.maximum_power
            else False,
            target_pressure_status=target_pressure_status,
        )

    def get_max_standard_rate(
        self,
        suction_pressure: float,
        discharge_pressure: float,
    ) -> float:
        """
        Calculate the maximum standard volume rate [Sm3/day] that the compressor train can operate at.

        This method determines the maximum rate by evaluating the compressor train's capacity
        based on the given suction and discharge pressures. It considers the compressor's
        operational constraints, including the maximum allowable power and the compressor chart limits.

        Args:
            suction_pressure (float): Suction pressure in bar absolute [bara].
            discharge_pressure (float): Discharge pressure in bar absolute [bara].

        Returns:
            float: The maximum standard volume rate in Sm3/day. Returns NaN if the calculation fails.
        """
        inlet_stream = self.fluid.get_fluid_stream(
            pressure_bara=suction_pressure,
            temperature_kelvin=self.stages[0].inlet_temperature_kelvin,
        )

        self.target_suction_pressure = inlet_stream.pressure_bara
        self.target_discharge_pressure = discharge_pressure
        try:
            max_mass_rate = self._get_max_mass_rate_single_timestep(
                target_discharge_pressure=discharge_pressure,
                inlet_stream=inlet_stream,  # inlet stream contains suction pressure
            )
        except EcalcError as e:
            logger.exception(e)
            max_mass_rate = float("nan")

        return self.fluid.mass_rate_to_standard_rate(mass_rate_kg_per_hour=max_mass_rate)

    def _get_max_mass_rate_single_timestep(
        self,
        target_discharge_pressure: float,
        inlet_stream: FluidStream,  # inlet stream contains suction pressure
        allow_asv: bool = False,
    ) -> float:
        """
        Calculate the maximum mass rate [kg/hour] that the compressor train can operate at for a single time step.

        This method determines the maximum mass rate based on the given suction and discharge pressures,
        considering the compressor's operational constraints, including capacity limits and pressure control mechanisms.

        The solution is determined as follows:
        1. If the compressor train cannot reach the target discharge pressure, return 0.
        2. If the solution lies along the compressor chart curve, iterate on the mass rate to find the solution.
        3. If the discharge pressure is too high, adjust using pressure control mechanisms (e.g., upstream or downstream choking).
        4. If no valid solution exists using pressure controls, return 0.

        Args:
            target_discharge_pressure (float): Target discharge pressure in bar absolute [bara].
            inlet_stream (FluidStream): The inlet stream containing suction pressure and other fluid properties.
            allow_asv (bool): If True, allows searching for solutions below the minimum mass rate using ASV recirculation.

        Returns:
            float: The maximum mass rate in kilograms per hour [kg/hour]. Returns 0 if no valid solution exists.
        """

        inlet_density = inlet_stream.density

        def _calculate_train_result(mass_rate: float) -> CompressorTrainResultSingleTimeStep:
            """Partial function of self.calculate_compressor_train_given_speed
            where we only pass mass_rate.
            """
            return self.calculate_single_speed_train(
                train_inlet_stream=inlet_stream,
                mass_rate_kg_per_hour_per_stage=[mass_rate] * self.number_of_compressor_stages,
            )

        def _calculate_train_result_given_ps_pd(mass_rate: float) -> CompressorTrainResultSingleTimeStep:
            """Partial function of self._evaluate_rate_ps_pd
            where we only pass mass_rate.
            """
            return self._evaluate_rate_ps_pd(
                rate=inlet_stream.mass_rate_to_standard_rate(mass_rate_kg_per_hour=mass_rate),
                suction_pressure=inlet_stream.pressure_bara,
                discharge_pressure=target_discharge_pressure,
            )

        # Using first stage as absolute (initial) bounds on min and max rate at max speed. Checking validity later.
        min_mass_rate_first_stage = self.stages[0].compressor_chart.minimum_rate * inlet_density
        max_mass_rate_first_stage = self.stages[0].compressor_chart.maximum_rate * inlet_density

        result_min_mass_rate_first_stage = _calculate_train_result(mass_rate=min_mass_rate_first_stage)
        result_max_mass_rate_first_stage = _calculate_train_result(mass_rate=max_mass_rate_first_stage)

        # Ensure that the minimum mass rate valid for the whole train.
        if not result_min_mass_rate_first_stage.within_capacity:
            #  * The following is a theoretically possible but very stupid configuration....
            #     First check if EPSILON is a valid rate. If not a valid rate does not exist.
            #     If EPSILON is valid, it will be the minimum rate. Then use maximize_x_given...() to find maximum rate
            #     somewhere between EPSILON and min_mass_rate_first_stage.
            # no result (return 0.0) or max_mass_rate_will also be set
            if allow_asv:
                if not _calculate_train_result(mass_rate=EPSILON).within_capacity:
                    logger.debug(
                        "There are no valid mass rate for SingleSpeedCompressorTrain."
                        "Infeasible solution. Returning max rate 0.0 (None)."
                    )
                    return 0.0
                min_mass_rate = EPSILON
                result_min_mass_rate = _calculate_train_result(mass_rate=min_mass_rate)
                max_mass_rate = maximize_x_given_boolean_condition_function(
                    x_min=EPSILON,  # Searching between near zero and the invalid mass rate above.
                    x_max=min_mass_rate_first_stage,
                    bool_func=lambda x: _calculate_train_result(mass_rate=x).within_capacity,
                    convergence_tolerance=1e-3,
                    maximum_number_of_iterations=20,
                )
                result_max_mass_rate = _calculate_train_result(mass_rate=max_mass_rate)
            else:
                logger.debug(
                    "There are no valid common mass rate for SingleSpeedCompressorTrain, and ASV is not allowed."
                    "Infeasible solution. Returning max rate 0.0 (None)."
                )
                return 0.0
        else:
            min_mass_rate = min_mass_rate_first_stage
            result_min_mass_rate = result_min_mass_rate_first_stage

            # Ensuring that the maximum mass rate is valid for the whole train.
            if not result_max_mass_rate_first_stage.within_capacity:
                max_mass_rate = maximize_x_given_boolean_condition_function(
                    x_min=min_mass_rate,
                    x_max=max_mass_rate_first_stage,
                    bool_func=lambda x: _calculate_train_result(mass_rate=x).within_capacity,
                    convergence_tolerance=1e-3,
                    maximum_number_of_iterations=20,
                )
                result_max_mass_rate = _calculate_train_result(mass_rate=max_mass_rate)
            else:
                max_mass_rate = max_mass_rate_first_stage
                result_max_mass_rate = result_max_mass_rate_first_stage

        # Solution scenario 1. Infeasible. Target pressure is too high.
        if result_min_mass_rate.discharge_pressure < target_discharge_pressure:
            return 0.0

        # Solution scenario 2. Solution is at the single speed curve.
        elif target_discharge_pressure >= result_max_mass_rate.discharge_pressure:
            """
            This is really equivalent to using ASV pressure control...? Search along speed curve for solution.
            """
            result_mass_rate = find_root(
                lower_bound=min_mass_rate,
                upper_bound=max_mass_rate,
                func=lambda x: _calculate_train_result(mass_rate=x).discharge_pressure - target_discharge_pressure,
                relative_convergence_tolerance=1e-3,
                maximum_number_of_iterations=20,
            )
            compressor_train_result = _calculate_train_result(mass_rate=result_mass_rate)
            return self._check_maximum_rate_against_maximum_power(
                maximum_mass_rate=compressor_train_result.mass_rate_kg_per_hour,
                suction_pressure=inlet_stream.pressure_bara,
                discharge_pressure=target_discharge_pressure,
            )

        # If solution not found along chart curve, and pressure control is DOWNSTREAM_CHOKE, run at max_mass_rate
        elif self.data_transfer_object.pressure_control == FixedSpeedPressureControl.DOWNSTREAM_CHOKE:
            if self._evaluate_rate_ps_pd(
                rate=inlet_stream.mass_rate_to_standard_rate(mass_rate_kg_per_hour=max_mass_rate),
                suction_pressure=inlet_stream.pressure_bara,
                discharge_pressure=target_discharge_pressure,
            ).is_valid:
                return self._check_maximum_rate_against_maximum_power(
                    maximum_mass_rate=max_mass_rate,
                    suction_pressure=inlet_stream.pressure_bara,
                    discharge_pressure=target_discharge_pressure,
                )

        # If solution not found along chart curve, and pressure control is UPSTREAM_CHOKE, find new max_mass_rate
        # with the new reduced suction pressure.
        elif self.data_transfer_object.pressure_control == FixedSpeedPressureControl.UPSTREAM_CHOKE:
            # lowering the inlet pressure using upstream choke will alter the max mass rate
            max_mass_rate_with_upstream_choke = maximize_x_given_boolean_condition_function(
                x_min=min_mass_rate,
                x_max=max_mass_rate_first_stage,
                bool_func=lambda x: _calculate_train_result_given_ps_pd(mass_rate=x).within_capacity,
                convergence_tolerance=1e-3,
                maximum_number_of_iterations=20,
            )
            return self._check_maximum_rate_against_maximum_power(
                maximum_mass_rate=max_mass_rate_with_upstream_choke,
                suction_pressure=inlet_stream.pressure_bara,
                discharge_pressure=target_discharge_pressure,
            )

        # Solution scenario 3. Too high pressure even at max flow rate. No pressure control mechanisms.
        elif result_max_mass_rate.discharge_pressure > target_discharge_pressure:
            return 0.0

        msg = "You should not end up here. Please contact eCalc support."
        logger.exception(msg)
        raise IllegalStateException(msg)

    def _check_maximum_rate_against_maximum_power(
        self, maximum_mass_rate: float, suction_pressure: float, discharge_pressure: float
    ) -> float:
        """Check if the maximum_rate, suction and discharge pressure power requirement exceeds a potential maximum power

        Args:
            maximum_mass_rate:  Found maximum mass rate for the train (at given suction and discharge pressure)
            suction_pressure: Suction pressure for the train
            discharge_pressure: Discharge pressure for the train

        Returns:
            Maximum rate constrained by maximum power (set to 0 if required power > maximum power)
        """
        if self.data_transfer_object.maximum_power:
            if (
                self._evaluate_rate_ps_pd(
                    rate=self.fluid.mass_rate_to_standard_rate(mass_rate_kg_per_hour=maximum_mass_rate),
                    suction_pressure=suction_pressure,
                    discharge_pressure=discharge_pressure,
                ).power_megawatt
                > self.data_transfer_object.maximum_power
            ):
                return 0.0

        return maximum_mass_rate
