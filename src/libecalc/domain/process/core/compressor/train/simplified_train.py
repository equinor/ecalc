import math
from abc import abstractmethod

import numpy as np
from numpy.typing import NDArray

from libecalc.common.errors.exceptions import IllegalStateException
from libecalc.common.fluid import FluidStream as FluidStreamDTO
from libecalc.common.logger import logger
from libecalc.common.units import UnitConstants
from libecalc.domain.process.core.chart.chart_area_flag import ChartAreaFlag
from libecalc.domain.process.core.compressor.results import (
    CompressorTrainResultSingleTimeStep,
    CompressorTrainStageResultSingleTimeStep,
)
from libecalc.domain.process.core.compressor.train.base import CompressorTrainModel
from libecalc.domain.process.core.compressor.train.chart import VariableSpeedCompressorChart
from libecalc.domain.process.core.compressor.train.chart.chart_creator import CompressorChartCreator
from libecalc.domain.process.core.compressor.train.fluid import FluidStream
from libecalc.domain.process.core.compressor.train.stage import CompressorTrainStage, UndefinedCompressorStage
from libecalc.domain.process.core.compressor.train.utils.enthalpy_calculations import (
    calculate_enthalpy_change_head_iteration,
    calculate_polytropic_head_campbell,
)
from libecalc.domain.process.core.compressor.utils import map_compressor_train_stage_to_domain
from libecalc.domain.process.dto import (
    CompressorTrainSimplifiedWithKnownStages,
    CompressorTrainSimplifiedWithUnknownStages,
)


class CompressorTrainSimplified(CompressorTrainModel):
    """A simplified model of a compressor train.

    In general, a compressor train (series of compressors) are running with the same shaft, meaning they will always
    have the same speed. Given inlet fluid conditions (composition, temperature, pressure, rate) and a shaft speed, the
    intermediate pressures (and temperature before cooling) between stages and the outlet pressure (and temperature) is
    given. To solve this for a given outlet pressure, one must iterate to find the speed.

    Simplification:
    The simplified approach used here, will instead make an assumption on the pressure ratio per stage and neglect
    the common shaft speed. Given an inlet and an outlet pressure for the train, the pressure ration for each stage is
    assumed equal and with this the inter-stage pressures are calculated. From this, the theoretical work is calculated
    for each compressor independently, neglecting the common shaft dependency.

    float of compressors:
    There are in essence two ways of determining the number of compressors in the train:
    - Either with a compressor chart generator model with a predefined number of charts - one for each compressor.
    - Or, when using a compressor chart generator model where charts are estimated on input data together with
      setting compressor_maximum_pressure_ratio. In this case, the maximum total pressure ratio is found from the input
      data and the number of compressors are set such that this maximum is not exceeded for any of the stages.

    Compressor chart (generator):
    For the simplified models, generic charts which are calculated at run-time is used, thus we do not have the chart
    up front, but need to calculate the chart at run-time, thus it uses chart-generators instead of charts directly.

    There are three options to specify the compressor chart for each compressor in the train, two of these based on a
    generic unified compressor chart which is scaled given a certain design point
    1. Design point for each compressor train is automatically calculated from the input data such that the chart "just"
       cover the maximum rate/head in the input.
    2. Design point for each compressor stage is specified in the input. Useful to e.g. rerun the same compressor train
       for a different set of input data after first running with automatically calculated design points
    3.  Compressor chart for each stage is specified in the input. Not yet implemented, will come later
    The compressor chart generator object, is an object which returns a compressor chart for each stage based on the
    compressor chart model chosen.

    FluidStream:
    Model of the fluid. See FluidStream

    Compressor inlet temperature:
    As a simplification, it is assumed that all compressor stages has the same inlet temperature (e.g. that there is an
    inter-stage cooling which always cool to the same temperature and that this is also equal at inlet of the first
    compressor).

    This class is meant as a template class, and the sub types for each compressor chart model is a subclass of this
    - Use CompressorTrainSimplifiedChartsEstimated for a compressor chart model where design points are automatically
      calculated from input data and used to scale the generic unified chart
    - Use CompressorTrainSimplifiedChartsFromDesignPoints for a compressor chart model where design points per stage are
      given and the generic unified chart is scaled by these.
    """

    @abstractmethod
    def get_stages(
        self,
        rate: NDArray[np.float64],
        suction_pressure: NDArray[np.float64],
        discharge_pressure: NDArray[np.float64],
    ) -> list[CompressorTrainStage]:
        """Implemented in subclasses."""
        raise NotImplementedError

    def _evaluate_rate_ps_pd(
        self,
        rate: NDArray[np.float64],
        suction_pressure: NDArray[np.float64],
        discharge_pressure: NDArray[np.float64],
    ) -> list[CompressorTrainResultSingleTimeStep]:
        """Calculate pressure ratios, find maximum pressure ratio, number of compressors in
        train and pressure ratio per stage Calculate fluid mass rate per hour
        Calculate results per compressor in train given mass rate and inter stage pressures.

        Note:
            When number of compressors in the train are not defined,
            then we figure out how many we need based on the rate and pressure data used for evaluation.

            Note! This does not play well with compressor systems, since the number of stages may change with different
            rates used.

        :param rate: Rate values [Sm3/day]
        :param suction_pressure: suction pressure [bara]
        :param discharge_pressure: discharge pressure [bara]
        :return: train result
        """
        if isinstance(self, CompressorTrainSimplifiedUnknownStages):
            self.stages = self.get_stages(
                rate=rate, suction_pressure=suction_pressure, discharge_pressure=discharge_pressure
            )

        pressure_ratios_per_stage = self.calculate_pressure_ratios_per_stage(
            suction_pressure=suction_pressure, discharge_pressure=discharge_pressure
        )

        mass_rate_kg_per_hour = self.fluid.standard_rate_to_mass_rate(standard_rates=rate)
        compressor_stages_result_per_time_step = []
        compressor_result_per_time_step = []
        inlet_pressure = suction_pressure.copy()
        for stage in self.stages:
            inlet_temperatures_kelvin = np.full_like(rate, fill_value=stage.inlet_temperature_kelvin, dtype=float)
            compressor_stage_result = self.calculate_compressor_stage_work_given_outlet_pressure(
                inlet_pressure=inlet_pressure,
                mass_rate_kg_per_hour=mass_rate_kg_per_hour,
                pressure_ratio=pressure_ratios_per_stage,
                inlet_temperature_kelvin=inlet_temperatures_kelvin,
                stage=stage,
            )

            compressor_stages_result_per_time_step.append(compressor_stage_result)
            inlet_pressure = inlet_pressure * pressure_ratios_per_stage

        # Converting from individual stage results to a train results and adding max rate per time step.
        for time_step in range(len(compressor_stages_result_per_time_step[0])):
            self.target_suction_pressure = suction_pressure[time_step]
            self.target_discharge_pressure = discharge_pressure[time_step]
            compressor_result_per_time_step.append(
                CompressorTrainResultSingleTimeStep(
                    speed=np.nan,
                    stage_results=[result[time_step] for result in compressor_stages_result_per_time_step],
                    target_pressure_status=self.check_target_pressures(
                        calculated_suction_pressure=compressor_stages_result_per_time_step[0][time_step].inlet_pressure,
                        calculated_discharge_pressure=compressor_stages_result_per_time_step[-1][
                            time_step
                        ].discharge_pressure,
                    ),
                    inlet_stream=compressor_stages_result_per_time_step[0][time_step].inlet_stream,
                    outlet_stream=compressor_stages_result_per_time_step[-1][time_step].outlet_stream,
                )
            )

        return compressor_result_per_time_step

    def calculate_compressor_stage_work_given_outlet_pressure(
        self,
        inlet_pressure: NDArray[np.float64],
        mass_rate_kg_per_hour: NDArray[np.float64],
        pressure_ratio: NDArray[np.float64],
        inlet_temperature_kelvin: NDArray[np.float64],
        stage: CompressorTrainStage | UndefinedCompressorStage,
        adjust_for_chart: bool = True,
    ) -> list[CompressorTrainStageResultSingleTimeStep]:
        outlet_pressure = np.multiply(inlet_pressure, pressure_ratio)

        inlet_streams = self.fluid.get_fluid_streams(
            pressure_bara=inlet_pressure, temperature_kelvin=inlet_temperature_kelvin
        )
        inlet_densities_kg_per_m3 = np.asarray([stream.density for stream in inlet_streams])
        inlet_actual_rate_m3_per_hour = mass_rate_kg_per_hour / inlet_densities_kg_per_m3

        # To avoid passing empty arrays down to the enthalpy calculation.
        if any(mass_rate_kg_per_hour > 0):
            if not isinstance(stage, UndefinedCompressorStage):
                efficiency_as_function_of_rate_and_head = stage.compressor_chart.efficiency_as_function_of_rate_and_head
            else:
                # Static efficiency regardless of rate and head. This happens if Generic chart from input is used.
                def efficiency_as_function_of_rate_and_head(rates, heads):
                    return np.full_like(rates, fill_value=stage.polytropic_efficiency, dtype=float)

            polytropic_enthalpy_change_joule_per_kg, polytropic_efficiency = calculate_enthalpy_change_head_iteration(
                inlet_streams=inlet_streams,
                inlet_temperature_kelvin=inlet_temperature_kelvin,
                inlet_pressure=inlet_pressure,
                outlet_pressure=outlet_pressure,
                molar_mass=self.fluid.molar_mass_kg_per_mol,
                polytropic_efficiency_vs_rate_and_head_function=efficiency_as_function_of_rate_and_head,
                inlet_actual_rate_m3_per_hour=inlet_actual_rate_m3_per_hour,
            )

            # Chart corrections to rate and head
            if adjust_for_chart:
                head_joule_per_kg = polytropic_enthalpy_change_joule_per_kg * polytropic_efficiency
                if stage.compressor_chart is None:
                    stage.compressor_chart = CompressorChartCreator.from_rate_and_head_values(
                        actual_volume_rates_m3_per_hour=inlet_actual_rate_m3_per_hour,
                        heads_joule_per_kg=head_joule_per_kg,
                        polytropic_efficiency=stage.polytropic_efficiency,
                    )

                compressor_chart_result = stage.compressor_chart.evaluate_capacity_and_extrapolate_below_minimum(
                    actual_volume_rates=inlet_actual_rate_m3_per_hour,
                    heads=head_joule_per_kg,
                    extrapolate_heads_below_minimum=True,
                )
                asv_corrected_actual_rate_m3_per_hour = np.where(
                    inlet_actual_rate_m3_per_hour > 0,
                    compressor_chart_result.asv_corrected_rates,
                    inlet_actual_rate_m3_per_hour,
                )

                # We only correct the indices where head is calculated.
                head_idx = head_joule_per_kg > 0
                choke_corrected_polytropic_heads = np.where(
                    head_idx, compressor_chart_result.choke_corrected_heads, head_joule_per_kg
                )
                rate_has_recirc = np.where(head_idx, compressor_chart_result.rate_has_recirc, False)
                pressure_is_choked = np.where(head_idx, compressor_chart_result.pressure_is_choked, False)
                rate_exceeds_maximum = np.where(head_idx, compressor_chart_result.rate_exceeds_maximum, False)
                head_exceeds_maximum = np.where(head_idx, compressor_chart_result.head_exceeds_maximum, False)
                exceeds_capacity = np.where(head_idx, compressor_chart_result.exceeds_capacity, False)

                polytropic_enthalpy_change_to_use_joule_per_kg = np.divide(
                    choke_corrected_polytropic_heads, polytropic_efficiency
                )
                mass_rate_to_use_kg_per_hour = asv_corrected_actual_rate_m3_per_hour * inlet_densities_kg_per_m3
            else:
                polytropic_enthalpy_change_to_use_joule_per_kg = polytropic_enthalpy_change_joule_per_kg
                asv_corrected_actual_rate_m3_per_hour = inlet_actual_rate_m3_per_hour
                mass_rate_to_use_kg_per_hour = mass_rate_kg_per_hour
                rate_has_recirc = np.full_like(inlet_actual_rate_m3_per_hour, fill_value=False)
                pressure_is_choked = np.full_like(inlet_actual_rate_m3_per_hour, fill_value=False)
                rate_exceeds_maximum = np.full_like(inlet_actual_rate_m3_per_hour, fill_value=False)
                head_exceeds_maximum = np.full_like(inlet_actual_rate_m3_per_hour, fill_value=False)
                exceeds_capacity = np.full_like(inlet_actual_rate_m3_per_hour, fill_value=False)

        else:
            polytropic_enthalpy_change_to_use_joule_per_kg = np.full_like(inlet_actual_rate_m3_per_hour, fill_value=0.0)
            polytropic_enthalpy_change_joule_per_kg = np.full_like(inlet_actual_rate_m3_per_hour, fill_value=0.0)
            polytropic_efficiency = np.full_like(inlet_actual_rate_m3_per_hour, fill_value=np.nan)
            asv_corrected_actual_rate_m3_per_hour = inlet_actual_rate_m3_per_hour
            mass_rate_to_use_kg_per_hour = mass_rate_kg_per_hour
            rate_has_recirc = np.full_like(inlet_actual_rate_m3_per_hour, fill_value=False)
            pressure_is_choked = np.full_like(inlet_actual_rate_m3_per_hour, fill_value=False)
            rate_exceeds_maximum = np.full_like(inlet_actual_rate_m3_per_hour, fill_value=False)
            head_exceeds_maximum = np.full_like(inlet_actual_rate_m3_per_hour, fill_value=False)
            exceeds_capacity = np.full_like(inlet_actual_rate_m3_per_hour, fill_value=False)

            if stage.compressor_chart is None:
                stage.compressor_chart = CompressorChartCreator.from_rate_and_head_design_point(
                    design_head_joule_per_kg=0,
                    design_actual_rate_m3_per_hour=0,
                    polytropic_efficiency=stage.polytropic_efficiency,
                )

        outlet_streams = [
            stream.set_new_pressure_and_enthalpy_change(
                new_pressure=pressure, enthalpy_change_joule_per_kg=enthalpy_change
            )
            for stream, pressure, enthalpy_change in zip(
                inlet_streams,
                outlet_pressure,
                polytropic_enthalpy_change_to_use_joule_per_kg,
            )
        ]
        outlet_densities_kg_per_m3 = np.asarray([stream.density for stream in outlet_streams])

        power_mw = (
            mass_rate_to_use_kg_per_hour
            * polytropic_enthalpy_change_to_use_joule_per_kg
            / UnitConstants.SECONDS_PER_HOUR
            * UnitConstants.WATT_TO_MEGAWATT
        )
        # Set power to nan for points where compressor capacity is exceeded
        if exceeds_capacity is not None:
            power_mw[np.argwhere(exceeds_capacity)[:, 0]] = np.nan

        polytropic_enthalpy_change_kilo_joule_per_kg = polytropic_enthalpy_change_joule_per_kg * UnitConstants.TO_KILO

        compressor_result = []
        for i in range(len(power_mw)):
            if pressure_is_choked[i] and rate_has_recirc[i]:
                chart_area_flag = ChartAreaFlag.BELOW_MINIMUM_SPEED_AND_BELOW_MINIMUM_FLOW_RATE
            elif pressure_is_choked[i] and rate_exceeds_maximum[i]:
                chart_area_flag = ChartAreaFlag.BELOW_MINIMUM_SPEED_AND_ABOVE_MAXIMUM_FLOW_RATE
            elif rate_has_recirc[i]:
                chart_area_flag = ChartAreaFlag.BELOW_MINIMUM_FLOW_RATE
            elif rate_exceeds_maximum[i]:
                chart_area_flag = ChartAreaFlag.ABOVE_MAXIMUM_FLOW_RATE
            elif pressure_is_choked[i]:
                chart_area_flag = ChartAreaFlag.BELOW_MINIMUM_SPEED
            elif head_exceeds_maximum[i]:
                chart_area_flag = ChartAreaFlag.ABOVE_MAXIMUM_SPEED
            else:
                chart_area_flag = ChartAreaFlag.INTERNAL_POINT

            compressor_result.append(
                CompressorTrainStageResultSingleTimeStep(
                    inlet_stream=FluidStreamDTO.from_fluid_domain_object(fluid_stream=inlet_streams[i]),
                    outlet_stream=FluidStreamDTO.from_fluid_domain_object(fluid_stream=outlet_streams[i]),
                    inlet_actual_rate_asv_corrected_m3_per_hour=asv_corrected_actual_rate_m3_per_hour[i],
                    inlet_actual_rate_m3_per_hour=inlet_actual_rate_m3_per_hour[i],
                    standard_rate_sm3_per_day=mass_rate_kg_per_hour[i]
                    * 24.0
                    / inlet_streams[i].standard_conditions_density,
                    standard_rate_asv_corrected_sm3_per_day=mass_rate_to_use_kg_per_hour[i]
                    * 24
                    / inlet_streams[i].standard_conditions_density,
                    outlet_actual_rate_asv_corrected_m3_per_hour=mass_rate_to_use_kg_per_hour[i]
                    / outlet_densities_kg_per_m3[i],
                    outlet_actual_rate_m3_per_hour=mass_rate_kg_per_hour[i] / outlet_densities_kg_per_m3[i],
                    mass_rate_kg_per_hour=mass_rate_kg_per_hour[i],
                    mass_rate_asv_corrected_kg_per_hour=mass_rate_to_use_kg_per_hour[i],
                    power_megawatt=power_mw[i],
                    chart_area_flag=chart_area_flag,
                    polytropic_enthalpy_change_kJ_per_kg=polytropic_enthalpy_change_to_use_joule_per_kg[i] / 1000,
                    polytropic_enthalpy_change_before_choke_kJ_per_kg=polytropic_enthalpy_change_kilo_joule_per_kg[i],
                    polytropic_head_kJ_per_kg=(
                        polytropic_enthalpy_change_to_use_joule_per_kg[i] * polytropic_efficiency[i]
                    )
                    / 1000,
                    polytropic_efficiency=polytropic_efficiency[i],
                    rate_has_recirculation=rate_has_recirc[i],
                    rate_exceeds_maximum=rate_exceeds_maximum[i],
                    pressure_is_choked=pressure_is_choked[i],
                    head_exceeds_maximum=head_exceeds_maximum[i],
                    # Assuming choking and ASV. Valid points are to the left and below the compressor chart.
                    point_is_valid=~np.isnan(power_mw[i]),  # power_mw is set to np.NaN if invalid step.
                )
            )

        return compressor_result


class CompressorTrainSimplifiedKnownStages(CompressorTrainSimplified):
    def __init__(
        self,
        data_transfer_object: CompressorTrainSimplifiedWithKnownStages,
    ):
        """See CompressorTrainSimplified for explanation of a compressor train."""
        logger.debug(f"Creating CompressorTrainSimplifiedKnownStages with n_stages: {len(data_transfer_object.stages)}")
        super().__init__(data_transfer_object)
        self.data_transfer_object = data_transfer_object

    def get_stages(
        self,
        rate: NDArray[np.float64],
        suction_pressure: NDArray[np.float64],
        discharge_pressure: NDArray[np.float64],
    ) -> list[CompressorTrainStage]:
        return self.stages

    def get_max_standard_rate(
        self,
        suction_pressures: NDArray[np.float64],
        discharge_pressures: NDArray[np.float64],
    ) -> NDArray[np.float64]:
        """For each stage
          Setup streams for inlet and outlet
          Calculate z and kappa for inlet and outlet
          Set z and kappa equal to average of in and out
          Calculate polytropic head for z and kappa
          Find maximum actual volume rate given head for each stage
          Calculate corresponding standard rates for each stage
        Maximum rate is minimum of the maximum standard rates for all stages.
        """
        if self.stages is None:
            raise ValueError("Can't calculate max pressure when compressor stages are not defined.")

        use_stage_for_maximum_rate_calculation = np.asarray([stage.compressor_chart for stage in self.stages])
        if not use_stage_for_maximum_rate_calculation.any():
            msg = "Calculating maximum rate is not possible for when all compressor charts are generic from data"
            logger.error(msg)
            return np.full_like(suction_pressures, fill_value=np.nan, dtype=float)

        pressure_ratios_per_stage = self.calculate_pressure_ratios_per_stage(
            suction_pressure=suction_pressures, discharge_pressure=discharge_pressures
        )
        inlet_pressure_all_stages = self._calulate_inlet_pressure_stages(
            inlet_pressure=suction_pressures,
            pressure_ratios_per_stage=pressure_ratios_per_stage,
            number_of_stages=len(self.stages),
        )

        # Take out data only for stages used for calculating maximum rate
        # Stages with compressor charts which are estimated from input data are not used, as these have per definition
        # infinite capacity as it can always be enlarged to account for the rate needed
        stages_to_use = [stage for stage in self.stages if stage.compressor_chart]
        inlet_pressure_stages_to_use = [
            inlet_pressure
            for stage_number, inlet_pressure in enumerate(inlet_pressure_all_stages)
            if use_stage_for_maximum_rate_calculation[stage_number]
        ]
        inlet_temperatures_kelvin_to_use = [stage.inlet_temperature_kelvin for stage in stages_to_use]
        compressor_charts = [stage.compressor_chart for stage in stages_to_use]

        stages_maximum_standard_rates = [
            self.calculate_maximum_rate_given_outlet_pressure_all_calculation_points(
                inlet_pressure=inlet_pressure_stages_to_use[stage_number],
                compressor_chart=chart,
                pressure_ratio=pressure_ratios_per_stage,
                inlet_temperature_kelvin=np.full_like(
                    inlet_pressure_stages_to_use[stage_number], inlet_temperatures_kelvin_to_use[stage_number]
                ),
                fluid=self.fluid,
            )
            for stage_number, chart in enumerate(compressor_charts)
        ]

        # The first (0-index) axis of stages_maximum_standard_rates - the list elements - represent each stage
        # The second (1-index) axis of stages_maximum_standard_rates - each numpy array - represent each of the input
        # pressure points
        # Want to calculate the maximum over all stages, hence use axis=0 in numpy.amax
        maximum_rates = np.amin(
            a=stages_maximum_standard_rates,
            axis=0,
        )

        return maximum_rates

    @staticmethod
    def _calulate_inlet_pressure_stages(
        inlet_pressure: NDArray[np.float64],
        pressure_ratios_per_stage: NDArray[np.float64],
        number_of_stages: int,
    ) -> list[NDArray[np.float64]]:
        """Calculate inlet pressure at each stage given inlet pressure at first stage, pressure ratio per stage and the
        number of stages.
        """
        inlet_pressure_stages = []
        inlet_pressure_stage = inlet_pressure.copy()
        for _stage_number in range(number_of_stages):
            inlet_pressure_stages.append(inlet_pressure_stage.copy())
            inlet_pressure_stage *= pressure_ratios_per_stage
        return inlet_pressure_stages

    @staticmethod
    def calculate_maximum_rate_given_outlet_pressure_all_calculation_points(
        inlet_pressure: NDArray[np.float64],
        pressure_ratio: NDArray[np.float64],
        inlet_temperature_kelvin: NDArray[np.float64],
        fluid: FluidStream,
        compressor_chart: VariableSpeedCompressorChart,
    ):
        inlet_streams = fluid.get_fluid_streams(
            pressure_bara=inlet_pressure, temperature_kelvin=inlet_temperature_kelvin
        )
        maximum_actual_rates_am3_per_hour = [
            CompressorTrainSimplifiedKnownStages.calculate_maximum_rate_given_outlet_pressure_single_calculation_point(
                inlet_pressure=inlet_pressure_calculation_point,
                pressure_ratio=pressure_ratio_calculation_point,
                inlet_temperature_kelvin=inlet_temperature_kelvin_calculation_point,
                inlet_stream=inlet_stream_calculation_point,
                molar_mass=fluid.molar_mass_kg_per_mol,
                compressor_chart=compressor_chart,
                initial_guess_head_at_maximum_actual_volume_rate=float(
                    np.mean(compressor_chart.maximum_speed_curve.head_values)
                ),
            )
            for inlet_pressure_calculation_point, pressure_ratio_calculation_point, inlet_temperature_kelvin_calculation_point, inlet_stream_calculation_point in zip(
                inlet_pressure, pressure_ratio, inlet_temperature_kelvin, inlet_streams
            )
        ]
        inlet_densities_kg_per_m3 = [inlet_stream.density for inlet_stream in inlet_streams]
        maximum_mass_rates_kg_per_hour = [
            actual_rate * density
            for actual_rate, density in zip(maximum_actual_rates_am3_per_hour, inlet_densities_kg_per_m3)
        ]
        maximum_standard_rates = fluid.mass_rate_to_standard_rate(
            mass_rate_kg_per_hour=np.array(maximum_mass_rates_kg_per_hour)
        )

        return maximum_standard_rates

    @staticmethod
    def calculate_maximum_rate_given_outlet_pressure_single_calculation_point(
        inlet_pressure: float,
        pressure_ratio: float,
        inlet_temperature_kelvin: float,
        inlet_stream: FluidStream,
        molar_mass: float,
        compressor_chart: VariableSpeedCompressorChart,
        initial_guess_head_at_maximum_actual_volume_rate: float,
    ) -> float:
        outlet_pressure = inlet_pressure * pressure_ratio

        if pressure_ratio < 1:
            error_message = "Outlet pressure ratio can not be less than 1"
            logger.error(error_message)
            raise IllegalStateException(error_message)

        maximum_rate_function = compressor_chart.get_maximum_rate

        polytropic_head = initial_guess_head_at_maximum_actual_volume_rate

        z = inlet_stream.z
        kappa = inlet_stream.kappa

        maximum_actual_volume_rate_previous = 1e-5  # Small but finite number to avoid division by zero.
        converged = False
        i = 0
        expected_diff = 1e-3
        max_iterations = 20
        while not converged and i < max_iterations:
            maximum_actual_volume_rate: float = float(
                maximum_rate_function(
                    heads=polytropic_head,
                    extrapolate_heads_below_minimum=False,
                )
            )

            efficiency_array: NDArray[np.float64] = compressor_chart.efficiency_as_function_of_rate_and_head(
                rates=np.atleast_1d(maximum_actual_volume_rate),
                heads=np.atleast_1d(polytropic_head),
            )
            polytropic_efficiency = efficiency_array[0]

            polytropic_head = calculate_polytropic_head_campbell(
                polytropic_efficiency=polytropic_efficiency,
                kappa=kappa,
                z=z,
                molar_mass=molar_mass,
                pressure_ratios=pressure_ratio,
                temperatures_kelvin=inlet_temperature_kelvin,
            )
            enthalpy_change_joule_per_kg = polytropic_head / polytropic_efficiency

            outlet_stream = inlet_stream.set_new_pressure_and_enthalpy_change(
                new_pressure=outlet_pressure, enthalpy_change_joule_per_kg=enthalpy_change_joule_per_kg
            )

            # Set convergence criterion on actual volume rate
            diff = np.linalg.norm(maximum_actual_volume_rate - maximum_actual_volume_rate_previous) / np.linalg.norm(
                maximum_actual_volume_rate_previous
            )
            converged = diff < expected_diff

            # Update z and kappa estimates based on new outlet estimates
            z = (inlet_stream.z + outlet_stream.z) / 2.0
            kappa = (inlet_stream.kappa + outlet_stream.kappa) / 2.0
            maximum_actual_volume_rate_previous = maximum_actual_volume_rate

            i += 1

            if i == max_iterations:
                logger.error(
                    "Simplified train: calculate_maximum_rate_given_outlet_pressure_single_calculation_point"
                    f" did not converge after {max_iterations} iterations."
                    f" inlet_pressure: {inlet_pressure}"
                    f" pressure_ratio: {pressure_ratio}."
                    f" inlet_temperature_kelvin: {inlet_temperature_kelvin}."
                    f" molar_mass: {molar_mass}."
                    f" Final difference between target and results was {diff},"
                    f" while the convergence criterion is set to difference lower than {expected_diff}"
                    f" NOTE! We will use the closest result we got for further calculations."
                    " This should normally not happen. Please contact eCalc support."
                )

        return maximum_actual_volume_rate


class CompressorTrainSimplifiedUnknownStages(CompressorTrainSimplified):
    """A simplified compressor train model where the number of compressors is not known before run-time
    Based on input data at run time evaluation, the number of stages is calculated based on maximum pressure ratio per
    stage.
    There is only one compressor chart given which is used for all stages. This chart may be a generic chart for which
    the design point is determined at run time given the input variables.

    """

    def __init__(
        self,
        data_transfer_object: CompressorTrainSimplifiedWithUnknownStages,
    ):
        logger.debug("Creating CompressorTrainSimplifiedUnknownStages")
        super().__init__(data_transfer_object)
        self.data_transfer_object = data_transfer_object

    def get_stages(
        self,
        rate: NDArray[np.float64],
        suction_pressure: NDArray[np.float64],
        discharge_pressure: NDArray[np.float64],
    ) -> list[CompressorTrainStage]:
        if len(rate) == 0:
            # Unable to figure out stages and pressure ratios if there are no rates as input
            return []

        pressure_ratios = discharge_pressure / suction_pressure
        maximum_pressure_ratio = max(pressure_ratios)
        number_of_compressors = self._calculate_number_of_compressors_needed(
            total_maximum_pressure_ratio=maximum_pressure_ratio,
            compressor_maximum_pressure_ratio=self.data_transfer_object.maximum_pressure_ratio_per_stage,
        )

        return [
            map_compressor_train_stage_to_domain(self.data_transfer_object.stage) for _ in range(number_of_compressors)
        ]

    @staticmethod
    def _calculate_number_of_compressors_needed(
        total_maximum_pressure_ratio: float,
        compressor_maximum_pressure_ratio: float,
    ) -> int:
        """Calculate min number of compressors given a maximum pressure ratio per compressor (default 3.5)."""
        x = math.log(total_maximum_pressure_ratio) / math.log(compressor_maximum_pressure_ratio)
        return math.ceil(x)

    def get_max_standard_rate(
        self,
        suction_pressures: NDArray[np.float64],
        discharge_pressures: NDArray[np.float64],
    ) -> NDArray[np.float64]:
        """Max rate does not have a meaning when using unknown compressor stages."""
        return np.full_like(suction_pressures, fill_value=np.nan, dtype=float)
