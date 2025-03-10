import numpy as np
from numpy.typing import NDArray

from libecalc.common.errors.exceptions import EcalcError, IllegalStateException
from libecalc.common.fixed_speed_pressure_control import FixedSpeedPressureControl
from libecalc.common.fluid import FluidStream as FluidStreamDTO
from libecalc.common.logger import logger
from libecalc.domain.process.core.chart.chart_area_flag import ChartAreaFlag
from libecalc.domain.process.core.compressor.results import (
    CompressorTrainResultSingleTimeStep,
    CompressorTrainStageResultSingleTimeStep,
)
from libecalc.domain.process.core.compressor.train.base import CompressorTrainModel
from libecalc.domain.process.core.compressor.train.fluid import FluidStream
from libecalc.domain.process.core.compressor.train.stage import CompressorTrainStage
from libecalc.domain.process.core.compressor.train.utils.common import (
    PRESSURE_CALCULATION_TOLERANCE,
)
from libecalc.domain.process.core.compressor.train.utils.numeric_methods import (
    find_root,
    maximize_x_given_boolean_condition_function,
)
from libecalc.domain.process.core.results.compressor import TargetPressureStatus
from libecalc.domain.process.dto import SingleSpeedCompressorTrain

EPSILON = 1e-5


class SingleSpeedCompressorTrainCommonShaft(CompressorTrainModel):
    """A model of a compressor train with fixed speed.

    Compressor charts:
        The compressor charts must be pre-defined and based on one fixed speed

    FluidStream:
        Model of the fluid. See FluidStream

    Pressure control:
        Specifies which control mechanism is used to meet the requested discharge pressure target. Currently the
        following control options are supported:
            There are two choking options:
                "UPSTREAM_CHOKE": suction pressure is reduced (assuming an upstream choke valve) until target discharge
                    pressure is met
                "DOWNSTREAM_CHOKE": discharge pressure is reduced to target after calculations (assuming a downstream
                    choke valve)

            There are three anti-surge valve recirculation options. If there is only one compressor, these three
            options should provide the same result. For compressor trains with multiple compressors, the results will
            vary between the three methods:
                "INDIVIDUAL_ASV_RATE": The fluid rate is increased (assuming the anti-surge valve is used to do fluid
                    recirculation) to "move" to a lower head value which corresponds to the requested outlet pressure.
                    In a train with multiple compressor stages, it is assumed that each compressor has it's own asv,
                    and the rate is increased in each in a way that the fraction between the actual rate without asv
                    and the maximum rate is equal for all stages.

                    actual_rate_after_asv = actual_rate_without_asv +
                                            (compressor_max_actual_rate - actual_rate_without_asv) * asv_fraction
                    where asv_fraction is equal for all stages.

                    The distribution of asv-rate between stages is not necessarily the correct one, but it is one that
                    do distribute the recirculation needed consistently between the stages.

                "INDIVIDUAL_ASV_PRESSURE": The ratio between the discharge pressure and the suction pressure
                    is set to be equal for all compressors in the compressor train. Then the ASVs are used independently
                    to arrive at the required discharge pressure for each compressor.

                "COMMON_ASV": The anit-surge valve is set to operate over the entire train, not over individual
                    compressors. Hence, the mass rate going through each compressor will be constant over the entire
                    compressor train.

    Maximum discharge pressure: This is optional and is only supported if for "DOWNSTREAM_CHOKE" pressure control. For
    downstream choke, the discharge pressure is floating and is unlimited. In practice, there may be control mechanisms
    to avoid this pressure be too large (for security reasons). When this attribute is set, the points where the
    discharge pressure will be larger than this with a "normal" "DOWNSTREAM_CHOKE" pressure control, will be evaluated
    with "UPSTREAM_CHOKE" pressure control and have a discharge pressure equal to the maximum specified.

    For each stage, one must specify a (single/fixed speed) compressor chart, an inlet temperature and whether to remove
    liquids after compression and cooling. In addition one must specify the pressure drop from previous stage
    (may be 0).

    The compressor train may be evaluated by one inlet through the entire train (fluid spec and rate)
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
        rate: NDArray[np.float64],
        suction_pressure: NDArray[np.float64],
        discharge_pressure: NDArray[np.float64],
    ) -> list[CompressorTrainResultSingleTimeStep]:
        """Evaluate a single speed compressor train total power given rate, suction pressure and discharge pressure.
        The evaluation will be different depending on the pressure control chosen.

        For some time steps, the input for rate, suction pressure and discharge pressure may provide a point which
        is outside the capacity of one or more or the compressor stages. In these cases a failure_status describing
        the problem will be returned as part of the CompressorTrainResult.

        For other time steps it may not be possible to find a feasible solution - the target discharge pressure is
        either too high or too low given the rate and suction pressure. In these situations, calculations will still be
        performed, and results returned, including a failure_status telling that target discharge pressure is too high
        or too low. The returned results will in these cases have either no asv recirculation (target pressure too high,
        returning the results with maximum possible discharge pressure) or maximum recirculation (target pressure too
        low, returning the results with the lowest possible discharge pressure).

        :param rate: Standard volume rate [Sm3/day]
        :param suction_pressure: Suction pressure per time step [bara]
        :param discharge_pressure: Discharge pressure per time step [bara]
        """
        if self.maximum_discharge_pressure is not None:
            maximum_input_discharge_pressure = max(discharge_pressure)
            if maximum_input_discharge_pressure > self.maximum_discharge_pressure:
                raise ValueError(
                    f"Maximum dishcarge pressure in input data ({maximum_input_discharge_pressure}) is "
                    f"larger than maximum allowed discharge pressure in single speed compressor model"
                    f" ({self.maximum_discharge_pressure})"
                )
        mass_rates_kg_per_hour = self.fluid.standard_rate_to_mass_rate(standard_rates=rate)

        train_results = []
        for mass_rate_kg_per_hour, inlet_pressure, outlet_pressure in zip(
            mass_rates_kg_per_hour, suction_pressure, discharge_pressure
        ):
            self.target_suction_pressure = inlet_pressure
            self.target_discharge_pressure = outlet_pressure
            if self.pressure_control == FixedSpeedPressureControl.DOWNSTREAM_CHOKE:
                train_result = self._evaluate_train_result_downstream_choking(
                    mass_rate_kg_per_hour=mass_rate_kg_per_hour,
                    suction_pressure=inlet_pressure,
                    discharge_pressure=outlet_pressure,
                )
            elif self.pressure_control == FixedSpeedPressureControl.UPSTREAM_CHOKE:
                train_result = self._evaluate_train_results_upstream_choking(
                    mass_rate_kg_per_hour=mass_rate_kg_per_hour,
                    suction_pressure=inlet_pressure,
                    discharge_pressure=outlet_pressure,
                )
            elif self.pressure_control == FixedSpeedPressureControl.INDIVIDUAL_ASV_RATE:
                train_result = self._evaluate_train_result_individual_asv_rate(
                    mass_rate_kg_per_hour=mass_rate_kg_per_hour,
                    suction_pressure=inlet_pressure,
                    discharge_pressure=outlet_pressure,
                )
            elif self.pressure_control == FixedSpeedPressureControl.INDIVIDUAL_ASV_PRESSURE:
                train_result = self._evaluate_train_result_asv_pressure(
                    mass_rate_kg_per_hour=mass_rate_kg_per_hour,
                    suction_pressure=inlet_pressure,
                    discharge_pressure=outlet_pressure,
                )
            elif self.pressure_control == FixedSpeedPressureControl.COMMON_ASV:
                train_result = self._evaluate_train_result_common_asv(
                    mass_rate_kg_per_hour=mass_rate_kg_per_hour,
                    suction_pressure=inlet_pressure,
                    discharge_pressure=outlet_pressure,
                )
            else:
                raise ValueError(f"Pressure control {self.pressure_control} not supported")

            train_results.append(train_result)

        return train_results

    def _evaluate_train_result_downstream_choking(
        self,
        mass_rate_kg_per_hour: float,
        suction_pressure: float,
        discharge_pressure: float,
    ) -> CompressorTrainResultSingleTimeStep:
        """Evaluate a single speed compressor train total power given mass rate, suction pressure and discharge pressure
        assuming the discharge pressure is controlled to meet target by a downstream choke valve.

        :param mass_rate_kg_per_hour: Mass rate [kg/hour]
        :param suction_pressure: Suction pressure per time step [bara]
        :param discharge_pressure: Discharge pressure per time step [bara]
        :return: A list of results per compressor stage and a list of failure status per compressor stage
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
        """Evaluate a single speed compressor train total power given mass rate, suction pressure and discharge pressure
        assuming the discharge pressure is controlled to meet target by a choking the suction pressure upstream. As the
        train results are calculated as a forward model, flashing the fluid at each stage given the inlet conditions, an
        iterative algorithm is used to find the suction pressure that results in the target discharge pressure.

        :param mass_rate_kg_per_hour: Mass rate [kg/hour]
        :param suction_pressure: Suction pressure [bara]
        :param discharge_pressure: Discharge pressure [bara]
        :return: Results per compressor stage
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
        """Evaluate a single speed compressor train total power given mass rate, suction pressure and discharge pressure.
        Assuming the discharge pressure is controlled to meet target using the anti-surge valve(s) (ASVs) to increase
        the net rate until the head is decreased enough (in each compressor) to meet the target discharge pressure. For
        trains (multiple compressor stages), the recirculation is distributed between each compressor stage such that
        the asv_fraction in the following equation is equal for all stages:

        actual_rate_after_asv = actual_rate_without_asv +
                                (compressor_max_actual_rate - actual_rate_without_asv) * asv_fraction

        The asv_fraction that results in the target discharge pressure is found through an iterative algorithm, which
        includes flashing the fluid at each stage given the inlet conditions and the asv_fraction.

        :param mass_rate_kg_per_hour: Mass rate [kg/hour]
        :param suction_pressure: Suction pressure [bara]
        :param discharge_pressure: Discharge pressure [bara]
        :return: Results per compressor stage
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
        """Model of single speed compressor train where asv is used to meet target pressure assuming that the
        pressure ratios (discharge pressure / suction pressure=) is equal over all compressors in the compressor train.
        """
        if mass_rate_kg_per_hour > 0:
            inlet_stream_train = self.fluid.get_fluid_streams(
                pressure_bara=np.asarray([suction_pressure]),
                temperature_kelvin=np.asarray([self.stages[0].inlet_temperature_kelvin]),
            )[0]
            pressure_ratio_per_stage = self.calculate_pressure_ratios_per_stage(
                suction_pressure=suction_pressure,
                discharge_pressure=discharge_pressure,
            )
            inlet_stream_stage = outlet_stream_stage = inlet_stream_train
            stage_results = []
            for stage in self.stages:
                outlet_pressure_for_stage = inlet_stream_stage.pressure_bara * pressure_ratio_per_stage
                stage_result = calculate_single_speed_compressor_stage_given_target_discharge_pressure(
                    outlet_pressure_stage_bara=outlet_pressure_for_stage,
                    mass_rate_kg_per_hour=mass_rate_kg_per_hour,
                    inlet_stream_stage=inlet_stream_stage,
                    stage=stage,
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
                speed=np.nan,
                stage_results=stage_results,
                target_pressure_status=target_pressure_status,
            )
        else:
            return CompressorTrainResultSingleTimeStep.create_empty(number_of_stages=len(self.stages))

    def _evaluate_train_result_common_asv(
        self,
        mass_rate_kg_per_hour: float,
        suction_pressure: float,
        discharge_pressure: float,
    ) -> CompressorTrainResultSingleTimeStep:
        """Evaluate a single speed compressor train total power given mass rate, suction pressure and discharge pressure
        assuming the discharge pressure is controlled to meet target using the anti-surge valve (ASV) to increase
        the net rate until the head is increased enough (in each compressor) to meet the target discharge pressure. For
        trains (multiple compressor stages), the asv is taken to go over the entire train, meaning that the same
        mass rate will pass through all compressors.

        To find the mass rate (including recirculation) that results in the target discharge pressure,
        an iterative algorithm is used on the forward model which flash the fluid at each stage given the inlet conditions
        and the additional recirculated mass rate.

        :param mass_rate_kg_per_hour: Mass rate [kg/hour]
        :param suction_pressure: Suction pressure per time step [bara]
        :param discharge_pressure: Discharge pressure per time step [bara]
        :return: A list of results per compressor stage and a list of failure status per compressor stage
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

        :param mass_rate_kg_per_hour: Mass rate [kg/hour]
        :param inlet_pressure_train_bara: Inlet pressure per time step [bara]
        :return: A list of results per compressor stage
        """
        if mass_rate_kg_per_hour > 0:
            mass_rate_for_stages = self.number_of_compressor_stages * [mass_rate_kg_per_hour]
            train_inlet_stream = self.fluid.get_fluid_streams(
                pressure_bara=np.asarray([inlet_pressure_train_bara]),
                temperature_kelvin=np.asarray([self.stages[0].inlet_temperature_kelvin]),
            )[0]
            train_result = self.calculate_single_speed_train(
                train_inlet_stream=train_inlet_stream,
                mass_rate_kg_per_hour_per_stage=mass_rate_for_stages,
            )
        else:
            train_result = CompressorTrainResultSingleTimeStep.create_empty(number_of_stages=len(self.stages))

        return train_result

    def _evaluate_rate_pd(
        self,
        mass_rate_kg_per_hour: float,
        outlet_pressure_train_bara: float,
    ) -> CompressorTrainResultSingleTimeStep:
        """Evaluate a single speed compressor train total power given mass rates and outlet pressures (one per time step).
        Newton iteration is used on the forward model which flash the fluid at each stage given the inlet conditions to
        find the suction pressure that results in the target discharge pressure.

        :param mass_rate_kg_per_hour: Mass rate [kg/hour]
        :param outlet_pressure_train_bara: Discharge pressure per time step [bara]
        :return: Results per compressor stage
        """
        if mass_rate_kg_per_hour > 0:
            mass_rate_for_stages = self.number_of_compressor_stages * [mass_rate_kg_per_hour]

            # As the inlet stream depends on the inlet pressure,
            # iterate on the inlet pressure to meet requested discharge pressure
            def _calculate_train_result_given_inlet_pressure(
                inlet_pressure: float,
            ) -> CompressorTrainResultSingleTimeStep:
                """Note that we use outside variables for clarity and to avoid class instances."""
                train_inlet_stream = self.fluid.get_fluid_streams(
                    pressure_bara=np.asarray([inlet_pressure]),
                    temperature_kelvin=np.asarray([self.stages[0].inlet_temperature_kelvin]),
                )[0]
                train_result = self.calculate_single_speed_train(
                    train_inlet_stream=train_inlet_stream,
                    mass_rate_kg_per_hour_per_stage=mass_rate_for_stages,
                )
                return train_result

            result_inlet_pressure = find_root(
                lower_bound=EPSILON + self.stages[0].pressure_drop_ahead_of_stage,
                upper_bound=outlet_pressure_train_bara,
                func=lambda x: _calculate_train_result_given_inlet_pressure(inlet_pressure=x).discharge_pressure
                - outlet_pressure_train_bara,
            )

            compressor_train_result = _calculate_train_result_given_inlet_pressure(inlet_pressure=result_inlet_pressure)
        else:
            compressor_train_result = CompressorTrainResultSingleTimeStep.create_empty(
                number_of_stages=len(self.stages)
            )

        return compressor_train_result

    def _evaluate_ps_pd_minimum_mass_rate(
        self,
        inlet_pressure_train_bara: float,
        outlet_pressure_train_bara: float,
        minimum_mass_rate_kg_per_hour: float,
    ) -> CompressorTrainResultSingleTimeStep:
        """Evaluate a single speed compressor train total power given net mass rate, suction pressure and discharge
        pressure assuming the discharge pressure is controlled to meet target using the anti-surge valve(s) (ASVs) to
        increase the net rate until the head is reduced enough (in each compressor) to meet the target discharge
        pressure. For trains (multiple compressor stages), the asv is distributed between each compressor stage such
        that the asv_fraction in the following equation is equal for all stages:
        actual_rate_after_asv = actual_rate_without_asv
            + (compressor_max_actual_rate - actual_rate_without_asv) * asv_fraction
        To find the asv_fraction that results in the target discharge pressure, a Newton iteration is used on the
        forward model which flash the fluid at each stage given the inlet conditions and the asv_fraction.

        :param minimum_mass_rate_kg_per_hour: Mass rate which is the minimum gross mass rate for each stage [kg/hour]
        :param inlet_pressure_train_bara: Suction pressure per time step [bara]
        :param outlet_pressure_train_bara: Discharge pressure per time step [bara]
        :return: A list of results per compressor stage and a list of failure status per compressor stage
        """
        # Iterate on rate until pressures are met
        if minimum_mass_rate_kg_per_hour > 0:
            train_inlet_stream = self.fluid.get_fluid_streams(
                pressure_bara=np.asarray([inlet_pressure_train_bara]),
                temperature_kelvin=np.asarray([self.stages[0].inlet_temperature_kelvin]),
            )[0]

            def _calculate_train_result_given_asv_rate_margin(
                asv_rate_fraction: float,
            ) -> CompressorTrainResultSingleTimeStep:
                """Note that we use outside variables for clarity and to avoid class instances."""
                train_result = self.calculate_single_speed_train(
                    train_inlet_stream=train_inlet_stream,
                    mass_rate_kg_per_hour_per_stage=[minimum_mass_rate_kg_per_hour] * self.number_of_compressor_stages,
                    asv_rate_fraction=asv_rate_fraction,
                )
                return train_result

            minimum_asv_fraction = 0.0
            maximum_asv_fraction = 1.0
            train_result_for_minimum_asv_rate_fraction = _calculate_train_result_given_asv_rate_margin(
                asv_rate_fraction=minimum_asv_fraction
            )
            if (
                train_result_for_minimum_asv_rate_fraction.chart_area_status == ChartAreaFlag.ABOVE_MAXIMUM_FLOW_RATE
            ) or (outlet_pressure_train_bara > train_result_for_minimum_asv_rate_fraction.discharge_pressure):
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
            compressor_train_result = _calculate_train_result_given_asv_rate_margin(
                asv_rate_fraction=result_asv_rate_margin
            )
            return compressor_train_result
        else:
            # or should one recirculate up to minimum flow rate even if input is 0 rate?
            return CompressorTrainResultSingleTimeStep.create_empty(number_of_stages=len(self.stages))

    def _evaluate_ps_pd_constant_mass_rate(
        self,
        inlet_pressure_train_bara: float,
        outlet_pressure_train_bara: float,
        minimum_mass_rate_kg_per_hour: float,
    ) -> CompressorTrainResultSingleTimeStep:
        """Evaluate a single speed compressor train total power given net mass rate, suction pressure and
        discharge pressure assuming the discharge pressure is controlled to meet target using the anti-surge valve
        (ASV) to increase the net rate until the head is reduced enough (in each compressor) to meet the target
        discharge pressure.

        For trains (multiple compressor stages), the ASV circulates over the entire compressor train.
        To find the mass_rate that results in the target discharge pressure, a Newton iteration is used on the
        forward model which flash the fluid at each stage given the inlet conditions and the mass_rate.

        :param minimum_mass_rate_kg_per_hour: Mass rate which is the minimum gross mass rate for each stage [kg/hour]
        :param inlet_pressure_train_bara: Suction pressure per time step [bara]
        :param outlet_pressure_train_bara: Discharge pressure per time step [bara]
        :return: A list of results per compressor stage and a list of failure status per compressor stage
        """
        # Iterate on rate until pressures are met
        if minimum_mass_rate_kg_per_hour > 0:
            train_inlet_stream = self.fluid.get_fluid_streams(
                pressure_bara=np.asarray([inlet_pressure_train_bara]),
                temperature_kelvin=np.asarray([self.stages[0].inlet_temperature_kelvin]),
            )[0]

            def _calculate_train_result_given_mass_rate(
                mass_rate_kg_per_hour: float,
            ) -> CompressorTrainResultSingleTimeStep:
                stage_results = self.calculate_single_speed_train(
                    train_inlet_stream=train_inlet_stream,
                    mass_rate_kg_per_hour_per_stage=[mass_rate_kg_per_hour] * self.number_of_compressor_stages,
                )
                return stage_results

            def _calculate_train_result_given_additional_mass_rate(
                additional_mass_rate_kg_per_hour: float,
            ) -> CompressorTrainResultSingleTimeStep:
                stage_results = self.calculate_single_speed_train(
                    train_inlet_stream=train_inlet_stream,
                    mass_rate_kg_per_hour_per_stage=[minimum_mass_rate_kg_per_hour] * self.number_of_compressor_stages,
                    asv_additional_mass_rate=additional_mass_rate_kg_per_hour,
                    target_discharge_pressure=outlet_pressure_train_bara,
                )
                return stage_results

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
            compressor_train_result = _calculate_train_result_given_additional_mass_rate(
                additional_mass_rate_kg_per_hour=result_mass_rate - minimum_mass_rate_kg_per_hour
            )
            return compressor_train_result
        else:
            # or should one recirculate up to minimum flow rate even if input is 0 rate?
            return CompressorTrainResultSingleTimeStep.create_empty(number_of_stages=len(self.stages))

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
            speed=np.nan,
            stage_results=stage_results,
            above_maximum_power=sum([stage_result.power_megawatt for stage_result in stage_results])
            > self.maximum_power
            if self.maximum_power
            else False,
            target_pressure_status=target_pressure_status,
        )

    def get_max_standard_rate(
        self,
        suction_pressures: NDArray[np.float64],
        discharge_pressures: NDArray[np.float64],
    ) -> NDArray[np.float64]:
        """Calculate the max standard rate [Sm3/day] that the compressor train can operate at."""
        inlet_streams = self.fluid.get_fluid_streams(
            pressure_bara=suction_pressures,
            temperature_kelvin=np.full_like(suction_pressures, fill_value=self.stages[0].inlet_temperature_kelvin),
        )

        max_mass_rates = []
        for discharge_pressure, inlet_stream in zip(discharge_pressures, inlet_streams):
            self.target_suction_pressure = inlet_stream.pressure_bara
            self.target_discharge_pressure = discharge_pressure
            try:
                max_mass_rate = self._get_max_mass_rate_single_timestep(
                    target_discharge_pressure=discharge_pressure,
                    inlet_stream=inlet_stream,  # inlet stream contains suction pressure
                )
            except EcalcError as e:
                logger.exception(e)
                max_mass_rate = np.nan

            max_mass_rates.append(max_mass_rate)

        return np.array(self.fluid.mass_rate_to_standard_rate(mass_rate_kg_per_hour=np.array(max_mass_rates)))

    def _get_max_mass_rate_single_timestep(
        self,
        target_discharge_pressure: float,
        inlet_stream: FluidStream,  # inlet stream contains suction pressure
        allow_asv: bool = False,
    ) -> float:
        """Calculate the max standard rate [Sm3/day] that the compressor train can operate at for a single time step.
        The maximum rate can be found in several areas:

        * The compressor train can't reach the required target pressure -> Left of the chart.
        * The compressor train hits the required outlet pressure on the compressor chart curve.
        * The compressor train returns too high pressure which can be corrected by choking upstream or downstream.
        * The compressor train returns too high pressure -> Right of the chart.

        This is how we search for the solution:
        1. If the compressor train cannot reach the target pressure regardless of rate and ASV (if allowed). Return 0.
        2. Else if the solution is along the chart curve;
            then we iterate on mass rate along the chart curve to find a solution.
        3. Else if the pressure is too high and pressure control is enabled,
            Either choke pressure downstream, or check if potential to reduce pressure enough by choking upstream
        4. Else if the outlet pressure is still too high then the pressure points given are not valid.
            We return 0.
        :param target_discharge_pressure: Discharge pressure per time step [bara]
        :param inlet_stream: The stream at the inlet of the single speed compressor train
        :param allow_asv: Limits the solution search space. If allow_asv is True, the algorithm will also search for
            a solution below the minimum mass rate for the first compressor stage, if that minimum mass rate is not
            a valid rate for the entire compressor train.
        :return: Standard volume rate [Sm3/day]

        Note: We use this methods variable scope within the inner functions.
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
                rate=np.asarray([inlet_stream.mass_rate_to_standard_rate(mass_rate_kg_per_hour=mass_rate)]),
                suction_pressure=np.asarray([inlet_stream.pressure_bara]),
                discharge_pressure=np.asarray([target_discharge_pressure]),
            )[0]

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
                rate=np.asarray([inlet_stream.mass_rate_to_standard_rate(mass_rate_kg_per_hour=max_mass_rate)]),
                suction_pressure=np.asarray([inlet_stream.pressure_bara]),
                discharge_pressure=np.asarray([target_discharge_pressure]),
            )[0].is_valid:
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
                    rate=np.asarray([self.fluid.mass_rate_to_standard_rate(mass_rate_kg_per_hour=maximum_mass_rate)]),
                    suction_pressure=np.asarray([suction_pressure]),
                    discharge_pressure=np.asarray([suction_pressure]),
                )[0].power_megawatt
                > self.data_transfer_object.maximum_power
            ):
                return 0.0

        return maximum_mass_rate


def calculate_single_speed_compressor_stage_given_target_discharge_pressure(
    stage: CompressorTrainStage,
    inlet_stream_stage: FluidStream,
    mass_rate_kg_per_hour: float,
    outlet_pressure_stage_bara: float,
) -> CompressorTrainStageResultSingleTimeStep:
    result_no_recirculation = stage.evaluate(
        inlet_stream_stage=inlet_stream_stage,
        mass_rate_kg_per_hour=mass_rate_kg_per_hour,
        asv_additional_mass_rate=0,
    )
    # result_no_recirculation.inlet_stream.density_kg_per_m3 will have correct pressure and temperature
    # to find max mass rate, inlet_stream_stage will not
    max_recirculation = max(
        stage.compressor_chart.maximum_rate * result_no_recirculation.inlet_stream.density_kg_per_m3
        - mass_rate_kg_per_hour
        - EPSILON,
        0,
    )
    result_max_recirculation = stage.evaluate(
        inlet_stream_stage=inlet_stream_stage,
        mass_rate_kg_per_hour=mass_rate_kg_per_hour,
        asv_additional_mass_rate=max_recirculation,
    )
    if result_no_recirculation.discharge_pressure < outlet_pressure_stage_bara:
        return result_no_recirculation
    elif result_max_recirculation.discharge_pressure > outlet_pressure_stage_bara:
        return result_max_recirculation

    def _calculate_single_speed_compressor_stage(
        additional_mass_rate: float,
    ) -> CompressorTrainStageResultSingleTimeStep:
        return stage.evaluate(
            inlet_stream_stage=inlet_stream_stage,
            mass_rate_kg_per_hour=mass_rate_kg_per_hour,
            asv_additional_mass_rate=additional_mass_rate,
        )

    result_mass_rate = find_root(
        lower_bound=0,
        upper_bound=max_recirculation,
        func=lambda x: _calculate_single_speed_compressor_stage(additional_mass_rate=x).discharge_pressure
        - outlet_pressure_stage_bara,
    )

    return _calculate_single_speed_compressor_stage(result_mass_rate)
