import math

import numpy as np
from numpy.typing import NDArray

from libecalc.common.errors.exceptions import IllegalStateException
from libecalc.common.fluid import FluidStream as FluidStreamDTO
from libecalc.common.logger import logger
from libecalc.common.units import UnitConstants
from libecalc.domain.process.chart.chart_area_flag import ChartAreaFlag
from libecalc.domain.process.chart.compressor import VariableSpeedCompressorChart
from libecalc.domain.process.chart.compressor.chart_creator import CompressorChartCreator
from libecalc.domain.process.compressor.core.results import (
    CompressorTrainResultSingleTimeStep,
    CompressorTrainStageResultSingleTimeStep,
)
from libecalc.domain.process.compressor.core.train.base import CompressorTrainModel
from libecalc.domain.process.compressor.core.train.fluid import FluidStream
from libecalc.domain.process.compressor.core.train.stage import CompressorTrainStage, UndefinedCompressorStage
from libecalc.domain.process.compressor.core.train.train_evaluation_input import CompressorTrainEvaluationInput
from libecalc.domain.process.compressor.core.train.utils.enthalpy_calculations import (
    calculate_enthalpy_change_head_iteration,
    calculate_polytropic_head_campbell,
)
from libecalc.domain.process.compressor.core.utils import map_compressor_train_stage_to_domain
from libecalc.domain.process.compressor.dto import (
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

    def check_for_undefined_stages(
        self,
        rate: NDArray[np.float64],
        suction_pressure: NDArray[np.float64],
        discharge_pressure: NDArray[np.float64],
    ) -> None:
        # All stages are there, but compressor chart can still be None (GENERIC_FROM_INPUT)
        self.stages = self.define_undefined_stages(
            suction_pressure=suction_pressure,
            discharge_pressure=discharge_pressure,
        )
        pressure_ratios_per_stage = self.calculate_pressure_ratios_per_stage(
            suction_pressure=suction_pressure, discharge_pressure=discharge_pressure
        )
        stage_inlet_pressure = suction_pressure
        mass_rate_kg_per_hour = self.fluid.standard_rate_to_mass_rate(standard_rates=rate)
        for stage_number, stage in enumerate(self.stages):
            inlet_temperature_kelvin = np.full_like(rate, fill_value=stage.inlet_temperature_kelvin, dtype=float)
            inlet_streams = self.fluid.get_fluid_streams(
                pressure_bara=stage_inlet_pressure,
                temperature_kelvin=inlet_temperature_kelvin,
            )
            inlet_densities_kg_per_m3 = np.asarray([stream.density for stream in inlet_streams])
            inlet_actual_rate_m3_per_hour = mass_rate_kg_per_hour / inlet_densities_kg_per_m3
            stage_outlet_pressure = np.multiply(stage_inlet_pressure, pressure_ratios_per_stage)
            if isinstance(stage, UndefinedCompressorStage):
                # Static efficiency regardless of rate and head. This happens if Generic chart from input is used.
                def efficiency_as_function_of_rate_and_head(rates, heads):
                    return np.full_like(rates, fill_value=stage.polytropic_efficiency, dtype=float)

                polytropic_enthalpy_change_joule_per_kg, polytropic_efficiency = (
                    calculate_enthalpy_change_head_iteration(
                        inlet_streams=inlet_streams,
                        inlet_temperature_kelvin=inlet_temperature_kelvin,
                        inlet_pressure=stage_inlet_pressure,
                        outlet_pressure=stage_outlet_pressure,
                        molar_mass=self.fluid.molar_mass_kg_per_mol,
                        polytropic_efficiency_vs_rate_and_head_function=efficiency_as_function_of_rate_and_head,
                        inlet_actual_rate_m3_per_hour=inlet_actual_rate_m3_per_hour,
                    )
                )

                head_joule_per_kg = polytropic_enthalpy_change_joule_per_kg * polytropic_efficiency
                self.stages[stage_number] = CompressorTrainStage(
                    compressor_chart=CompressorChartCreator.from_rate_and_head_values(
                        actual_volume_rates_m3_per_hour=inlet_actual_rate_m3_per_hour,
                        heads_joule_per_kg=head_joule_per_kg,
                        polytropic_efficiency=stage.polytropic_efficiency,
                    ),
                    inlet_temperature_kelvin=stage.inlet_temperature_kelvin,
                    remove_liquid_after_cooling=stage.remove_liquid_after_cooling,
                    pressure_drop_ahead_of_stage=stage.pressure_drop_ahead_of_stage,
                )
            stage_inlet_pressure = stage_outlet_pressure

        return None

    def evaluate_given_constraints(
        self,
        constraints: CompressorTrainEvaluationInput,
    ) -> CompressorTrainResultSingleTimeStep:
        """
        Calculate pressure ratios, find maximum pressure ratio, number of compressors in
        the train, and pressure ratio per stage. Calculate fluid mass rate per hour and
        results per compressor in the train given mass rate and inter-stage pressures.

        Note:
            - When the number of compressors in the train is not defined, the method determines
            how many are needed based on the rate and pressure data used for evaluation.
            - This approach may not work well with compressor systems, as the number of stages
            may change with different rates.

        Returns:
            CompressorTrainResultSingleTimeStep: The result of the compressor train evaluation.
        """

        pressure_ratios_per_stage = self.calculate_pressure_ratios_per_stage(
            suction_pressure=constraints.suction_pressure, discharge_pressure=constraints.discharge_pressure
        )

        mass_rate_kg_per_hour = self.fluid.standard_rate_to_mass_rate(standard_rates=constraints.rate)
        if mass_rate_kg_per_hour > 0:
            compressor_stages_result = []
            inlet_pressure = constraints.suction_pressure.copy()
            for stage in self.stages:
                compressor_stage_result = self.calculate_compressor_stage_work_given_outlet_pressure(
                    inlet_pressure=inlet_pressure,
                    mass_rate_kg_per_hour=mass_rate_kg_per_hour,
                    pressure_ratio=pressure_ratios_per_stage,
                    inlet_temperature_kelvin=stage.inlet_temperature_kelvin,
                    stage=stage,
                )

                compressor_stages_result.append(compressor_stage_result)
                inlet_pressure = inlet_pressure * pressure_ratios_per_stage

            # Converting from individual stage results to a train results
            return CompressorTrainResultSingleTimeStep(
                speed=np.nan,
                stage_results=compressor_stages_result,
                target_pressure_status=self.check_target_pressures(
                    constraints=constraints,
                    results=compressor_stages_result,
                ),
                inlet_stream=compressor_stages_result[0].inlet_stream,
                outlet_stream=compressor_stages_result[-1].outlet_stream,
            )
        else:
            return CompressorTrainResultSingleTimeStep.create_empty(number_of_stages=len(self.stages))

    def calculate_compressor_stage_work_given_outlet_pressure(
        self,
        inlet_pressure: float,
        mass_rate_kg_per_hour: float,
        pressure_ratio: float,
        inlet_temperature_kelvin: float,
        stage: CompressorTrainStage,
        adjust_for_chart: bool = True,
    ) -> CompressorTrainStageResultSingleTimeStep:
        outlet_pressure = inlet_pressure * pressure_ratio

        inlet_stream = self.fluid.get_fluid_stream(
            pressure_bara=inlet_pressure, temperature_kelvin=inlet_temperature_kelvin
        )
        inlet_actual_rate_m3_per_hour = mass_rate_kg_per_hour / inlet_stream.density

        # To avoid passing empty arrays down to the enthalpy calculation.
        if mass_rate_kg_per_hour > 0:
            polytropic_enthalpy_change_joule_per_kg, polytropic_efficiency = calculate_enthalpy_change_head_iteration(
                inlet_streams=inlet_stream,
                inlet_temperature_kelvin=inlet_temperature_kelvin,
                inlet_pressure=inlet_pressure,
                outlet_pressure=outlet_pressure,
                molar_mass=self.fluid.molar_mass_kg_per_mol,
                polytropic_efficiency_vs_rate_and_head_function=stage.compressor_chart.efficiency_as_function_of_rate_and_head,
                inlet_actual_rate_m3_per_hour=inlet_actual_rate_m3_per_hour,
            )

            # Chart corrections to rate and head
            if adjust_for_chart:
                head_joule_per_kg = polytropic_enthalpy_change_joule_per_kg * polytropic_efficiency
                compressor_chart_result = stage.compressor_chart.evaluate_capacity_and_extrapolate_below_minimum(
                    actual_volume_rates=inlet_actual_rate_m3_per_hour,
                    heads=head_joule_per_kg,
                    extrapolate_heads_below_minimum=True,
                )
                asv_corrected_actual_rate_m3_per_hour = compressor_chart_result.asv_corrected_rates[0]
                choke_corrected_polytropic_head = compressor_chart_result.choke_corrected_heads[0]
                rate_has_recirc = compressor_chart_result.rate_has_recirc[0]
                pressure_is_choked = compressor_chart_result.pressure_is_choked[0]
                rate_exceeds_maximum = compressor_chart_result.rate_exceeds_maximum[0]
                head_exceeds_maximum = compressor_chart_result.head_exceeds_maximum[0]
                exceeds_capacity = compressor_chart_result.exceeds_capacity[0]

                polytropic_enthalpy_change_to_use_joule_per_kg = choke_corrected_polytropic_head / polytropic_efficiency
                mass_rate_to_use_kg_per_hour = asv_corrected_actual_rate_m3_per_hour * inlet_stream.density
            else:
                polytropic_enthalpy_change_to_use_joule_per_kg = polytropic_enthalpy_change_joule_per_kg
                asv_corrected_actual_rate_m3_per_hour = inlet_actual_rate_m3_per_hour
                mass_rate_to_use_kg_per_hour = mass_rate_kg_per_hour
                rate_has_recirc = False
                pressure_is_choked = False
                rate_exceeds_maximum = False
                head_exceeds_maximum = False
                exceeds_capacity = False

        else:
            polytropic_enthalpy_change_to_use_joule_per_kg = 0.0
            polytropic_enthalpy_change_joule_per_kg = 0.0
            polytropic_efficiency = np.nan
            asv_corrected_actual_rate_m3_per_hour = inlet_actual_rate_m3_per_hour
            mass_rate_to_use_kg_per_hour = mass_rate_kg_per_hour
            rate_has_recirc = False
            pressure_is_choked = False
            rate_exceeds_maximum = False
            head_exceeds_maximum = False
            exceeds_capacity = False

        outlet_stream = inlet_stream.set_new_pressure_and_enthalpy_change(
            new_pressure=outlet_pressure, enthalpy_change_joule_per_kg=polytropic_enthalpy_change_to_use_joule_per_kg
        )
        outlet_densities_kg_per_m3 = outlet_stream.density

        power_mw = (
            mass_rate_to_use_kg_per_hour
            * polytropic_enthalpy_change_to_use_joule_per_kg
            / UnitConstants.SECONDS_PER_HOUR
            * UnitConstants.WATT_TO_MEGAWATT
        )
        # Set power to nan for points where compressor capacity is exceeded
        if exceeds_capacity:
            power_mw = np.nan

        polytropic_enthalpy_change_kilo_joule_per_kg = polytropic_enthalpy_change_joule_per_kg * UnitConstants.TO_KILO

        if pressure_is_choked and rate_has_recirc:
            chart_area_flag = ChartAreaFlag.BELOW_MINIMUM_SPEED_AND_BELOW_MINIMUM_FLOW_RATE
        elif pressure_is_choked and rate_exceeds_maximum:
            chart_area_flag = ChartAreaFlag.BELOW_MINIMUM_SPEED_AND_ABOVE_MAXIMUM_FLOW_RATE
        elif rate_has_recirc:
            chart_area_flag = ChartAreaFlag.BELOW_MINIMUM_FLOW_RATE
        elif rate_exceeds_maximum:
            chart_area_flag = ChartAreaFlag.ABOVE_MAXIMUM_FLOW_RATE
        elif pressure_is_choked:
            chart_area_flag = ChartAreaFlag.BELOW_MINIMUM_SPEED
        elif head_exceeds_maximum:
            chart_area_flag = ChartAreaFlag.ABOVE_MAXIMUM_SPEED
        else:
            chart_area_flag = ChartAreaFlag.INTERNAL_POINT

        return CompressorTrainStageResultSingleTimeStep(
            inlet_stream=FluidStreamDTO.from_fluid_domain_object(fluid_stream=inlet_stream),
            outlet_stream=FluidStreamDTO.from_fluid_domain_object(fluid_stream=outlet_stream),
            inlet_actual_rate_asv_corrected_m3_per_hour=asv_corrected_actual_rate_m3_per_hour,
            inlet_actual_rate_m3_per_hour=inlet_actual_rate_m3_per_hour,
            standard_rate_sm3_per_day=mass_rate_kg_per_hour * 24.0 / inlet_stream.standard_conditions_density,
            standard_rate_asv_corrected_sm3_per_day=mass_rate_to_use_kg_per_hour
            * 24
            / inlet_stream.standard_conditions_density,
            outlet_actual_rate_asv_corrected_m3_per_hour=mass_rate_to_use_kg_per_hour / outlet_densities_kg_per_m3,
            outlet_actual_rate_m3_per_hour=mass_rate_kg_per_hour / outlet_densities_kg_per_m3,
            mass_rate_kg_per_hour=mass_rate_kg_per_hour,
            mass_rate_asv_corrected_kg_per_hour=mass_rate_to_use_kg_per_hour,
            power_megawatt=power_mw,
            chart_area_flag=chart_area_flag,
            polytropic_enthalpy_change_kJ_per_kg=polytropic_enthalpy_change_to_use_joule_per_kg / 1000,
            polytropic_enthalpy_change_before_choke_kJ_per_kg=polytropic_enthalpy_change_kilo_joule_per_kg,
            polytropic_head_kJ_per_kg=(polytropic_enthalpy_change_to_use_joule_per_kg * polytropic_efficiency) / 1000,
            polytropic_efficiency=polytropic_efficiency,
            rate_has_recirculation=rate_has_recirc,
            rate_exceeds_maximum=rate_exceeds_maximum,
            pressure_is_choked=pressure_is_choked,
            head_exceeds_maximum=head_exceeds_maximum,
            # Assuming choking and ASV. Valid points are to the left and below the compressor chart.
            point_is_valid=~np.isnan(power_mw),  # power_mw is set to np.NaN if invalid step.
        )


class CompressorTrainSimplifiedKnownStages(CompressorTrainSimplified):
    def __init__(
        self,
        data_transfer_object: CompressorTrainSimplifiedWithKnownStages,
    ):
        """See CompressorTrainSimplified for explanation of a compressor train."""
        logger.debug(f"Creating CompressorTrainSimplifiedKnownStages with n_stages: {len(data_transfer_object.stages)}")
        super().__init__(data_transfer_object)
        self.data_transfer_object = data_transfer_object

    def define_undefined_stages(
        self,
        suction_pressure: NDArray[np.float64],
        discharge_pressure: NDArray[np.float64],
    ) -> list[CompressorTrainStage]:
        return self.stages

    def get_max_standard_rate(
        self,
        suction_pressure: float,
        discharge_pressure: float,
    ) -> float:
        """Calculate the maximum standard rate for a single set of suction and discharge pressures.

        This method determines the maximum rate by evaluating the compressor train's capacity
        based on the given suction and discharge pressures. It considers the compressor's
        operational constraints, including the maximum allowable power and the compressor chart limits.

        Args:
            suction_pressure (float): Suction pressure in bar absolute [bara].
            discharge_pressure (float): Discharge pressure in bar absolute [bara].

        Returns:
            float: The maximum standard volume rate in Sm3/day. Returns NaN if the calculation fails.
        """
        if self.stages is None:
            raise ValueError("Can't calculate max pressure when compressor stages are not defined.")

        use_stage_for_maximum_rate_calculation = [stage.compressor_chart is not None for stage in self.stages]
        if not any(use_stage_for_maximum_rate_calculation):
            logger.error("Calculating maximum rate is not possible when all compressor charts are generic from data")
            return float("nan")

        pressure_ratios_per_stage = self.calculate_pressure_ratios_per_stage(
            suction_pressure=suction_pressure, discharge_pressure=discharge_pressure
        )
        inlet_pressure_all_stages = self._calculate_inlet_pressure_stages(
            inlet_pressure=suction_pressure,
            pressure_ratio_per_stage=pressure_ratios_per_stage,
            number_of_stages=len(self.stages),
        )

        # Filter stages used for calculating maximum rate
        stages_to_use = [stage for stage, use in zip(self.stages, use_stage_for_maximum_rate_calculation) if use]
        inlet_pressure_stages_to_use = [
            inlet_pressure
            for inlet_pressure, use in zip(inlet_pressure_all_stages, use_stage_for_maximum_rate_calculation)
            if use
        ]
        inlet_temperatures_kelvin_to_use = [stage.inlet_temperature_kelvin for stage in stages_to_use]
        compressor_charts = [stage.compressor_chart for stage in stages_to_use]

        # Calculate maximum standard rate for each stage (excluding generic from input charts)
        stages_maximum_standard_rates = [
            self.calculate_maximum_rate_for_stage(
                inlet_pressure=inlet_pressure_stages_to_use[stage_number],
                compressor_chart=chart,
                pressure_ratio=pressure_ratios_per_stage,
                inlet_temperature_kelvin=inlet_temperatures_kelvin_to_use[stage_number],
                fluid=self.fluid,
            )
            for stage_number, chart in enumerate(compressor_charts)
        ]

        # Return the minimum of the maximum rates across all stages
        return min(stages_maximum_standard_rates)

    @staticmethod
    def _calculate_inlet_pressure_stages(
        inlet_pressure: float,
        pressure_ratio_per_stage: float,
        number_of_stages: int,
    ) -> list[float]:
        """Calculate inlet pressure at each stage given inlet pressure at first stage, pressure ratio per stage, and the
        number of stages.
        """
        inlet_pressure_stages = []
        inlet_pressure_stage = inlet_pressure
        for _ in range(number_of_stages):
            inlet_pressure_stages.append(inlet_pressure_stage)
            inlet_pressure_stage *= pressure_ratio_per_stage
        return inlet_pressure_stages

    @staticmethod
    def calculate_maximum_rate_for_stage(
        inlet_pressure: float,
        pressure_ratio: float,
        inlet_temperature_kelvin: float,
        fluid: FluidStream,
        compressor_chart: VariableSpeedCompressorChart,
    ) -> float:
        """Calculate the maximum standard rate for a single set of inputs."""
        inlet_stream = fluid.get_fluid_stream(pressure_bara=inlet_pressure, temperature_kelvin=inlet_temperature_kelvin)
        outlet_pressure = inlet_pressure * pressure_ratio

        if pressure_ratio < 1:
            error_message = "Outlet pressure ratio can not be less than 1"
            logger.error(error_message)
            raise IllegalStateException(error_message)

        maximum_rate_function = compressor_chart.get_maximum_rate
        polytropic_head = float(
            np.mean(compressor_chart.maximum_speed_curve.head_values)
        )  # Initial guess for polytropic head

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

            polytropic_efficiency = compressor_chart.efficiency_as_function_of_rate_and_head(
                rates=np.atleast_1d(maximum_actual_volume_rate),
                heads=np.atleast_1d(polytropic_head),
            )[0]

            polytropic_head = calculate_polytropic_head_campbell(
                polytropic_efficiency=polytropic_efficiency,
                kappa=kappa,
                z=z,
                molar_mass=fluid.molar_mass_kg_per_mol,
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
                    "Simplified train: calculate_maximum_rate_for_stage"
                    f" did not converge after {max_iterations} iterations."
                    f" inlet_pressure: {inlet_pressure}"
                    f" pressure_ratio: {pressure_ratio}."
                    f" inlet_temperature_kelvin: {inlet_temperature_kelvin}."
                    f" molar_mass: {fluid.molar_mass_kg_per_mol}."
                    f" Final difference between target and results was {diff},"
                    f" while the convergence criterion is set to difference lower than {expected_diff}"
                    f" NOTE! We will use the closest result we got for further calculations."
                    " This should normally not happen. Please contact eCalc support."
                )

        inlet_density_kg_per_m3 = inlet_stream.density
        maximum_mass_rate_kg_per_hour = maximum_actual_volume_rate * inlet_density_kg_per_m3
        maximum_standard_rate = fluid.mass_rate_to_standard_rate(mass_rate_kg_per_hour=maximum_mass_rate_kg_per_hour)

        return maximum_standard_rate


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

    def define_undefined_stages(
        self,
        suction_pressure: NDArray[np.float64],
        discharge_pressure: NDArray[np.float64],
    ) -> list[CompressorTrainStage]:
        if len(suction_pressure) == 0:
            # Unable to figure out stages and pressure ratios if there are no suction_pressures as input
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
        suction_pressure: float,
        discharge_pressure: float,
    ) -> float:
        """Max rate does not have a meaning when using unknown compressor stages."""
        return np.nan
