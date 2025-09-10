import abc
import math

import numpy as np

from libecalc.common.energy_model_type import EnergyModelType
from libecalc.common.errors.exceptions import IllegalStateException
from libecalc.common.logger import logger
from libecalc.common.units import UnitConstants
from libecalc.domain.component_validation_error import ProcessPressureRatioValidationException
from libecalc.domain.process.compressor.core.results import (
    CompressorTrainResultSingleTimeStep,
    CompressorTrainStageResultSingleTimeStep,
)
from libecalc.domain.process.compressor.core.train.base import CompressorTrainModel
from libecalc.domain.process.compressor.core.train.stage import CompressorTrainStage
from libecalc.domain.process.compressor.core.train.train_evaluation_input import CompressorTrainEvaluationInput
from libecalc.domain.process.compressor.core.train.utils.enthalpy_calculations import (
    calculate_enthalpy_change_head_iteration,
    calculate_polytropic_head_campbell,
)
from libecalc.domain.process.compressor.core.utils import map_compressor_train_stage_to_domain
from libecalc.domain.process.compressor.dto import CompressorStage
from libecalc.domain.process.value_objects.chart.chart_area_flag import ChartAreaFlag
from libecalc.domain.process.value_objects.chart.compressor import VariableSpeedCompressorChart
from libecalc.domain.process.value_objects.fluid_stream import FluidStream, ProcessConditions
from libecalc.domain.process.value_objects.fluid_stream.fluid_factory import FluidFactoryInterface


class CompressorTrainSimplified(CompressorTrainModel, abc.ABC):
    """A simplified model of a compressor train that assumes equal pressure ratios per stage.

    This model simplifies compressor train calculations by assuming each stage has an equal pressure ratio,
    which allows independent calculation of each compressor stage without iterating on shaft speed.
    Unlike detailed compressor train models that consider common shaft constraints, this model treats
    each stage independently for computational efficiency.

    Simplification approach:
    Given inlet and outlet pressures for the train, the pressure ratio for each stage is calculated as
    the nth root of the total pressure ratio (where n is the number of stages). Inter-stage pressures
    and theoretical work are calculated based on these equal pressure ratios, neglecting the common
    shaft speed dependency.

    Stage configuration:
    The number of compressor stages can be determined in two ways:
    - Known stages: Predefined number of stages with specific configurations
    - Unknown stages: Number determined at runtime based on maximum pressure ratios and stage limits

    All compressor stages are assumed to have the same inlet temperature, representing inter-stage
    cooling that maintains constant temperature between stages.

    Stages must be properly prepared with compressor charts before evaluation. Models validate stage
    preparation and raise IllegalStateException if stages are missing or undefined.
    """

    def set_prepared_stages(self, prepared_stages: list[CompressorTrainStage]) -> None:
        """Set the compressor train stages.

        Replaces the current stages with the provided list of prepared stages.
        The stages must have valid compressor charts for evaluation to succeed.

        Args:
            prepared_stages: List of CompressorTrainStage objects with compressor charts
        """
        self.stages = prepared_stages

    def calculate_pressure_ratios_per_stage(
        self,
        suction_pressure: np.ndarray | float,
        discharge_pressure: np.ndarray | float,
    ) -> np.ndarray | float:
        """Calculate pressure ratios per stage for simplified train models.

        Returns array if inputs are arrays, scalar if inputs are scalars.
        Each stage applies the nth root of the overall pressure ratio.
        """
        if len(self.stages) == 0:
            if isinstance(suction_pressure, np.ndarray):
                return np.ones_like(suction_pressure)
            else:
                return 1.0

        if isinstance(suction_pressure, np.ndarray):
            pressure_ratios = np.divide(
                discharge_pressure, suction_pressure, out=np.ones_like(suction_pressure), where=suction_pressure != 0
            )
            return pressure_ratios ** (1.0 / len(self.stages))
        else:
            pressure_ratios = discharge_pressure / suction_pressure
            return pressure_ratios ** (1.0 / len(self.stages))

    def _validate_stages_prepared(self) -> None:
        """Ensure model has valid prepared stages before evaluation.

        Raises:
            IllegalStateException: If model has no stages or contains undefined stages
        """
        if not self.stages:
            raise IllegalStateException(
                f"{type(self).__name__} has no stages. "
                "Use SimplifiedTrainBuilder.prepare_model_stages_from_data() "
                "to prepare stages before evaluation."
            )

        # Check for undefined stages that need preparation
        from libecalc.domain.process.compressor.core.train.stage import UndefinedCompressorStage

        undefined_stages = [i for i, stage in enumerate(self.stages) if isinstance(stage, UndefinedCompressorStage)]
        if undefined_stages:
            raise IllegalStateException(
                f"{type(self).__name__} contains undefined stages at positions {undefined_stages}. "
                "Use SimplifiedTrainBuilder.prepare_model_stages_from_data() "
                "to generate charts for undefined stages before evaluation."
            )

    def evaluate_given_constraints(
        self,
        constraints: CompressorTrainEvaluationInput,
    ) -> CompressorTrainResultSingleTimeStep:
        """Evaluate the compressor train for single-timestep operating constraints.

        Calculates compressor train performance by assuming equal pressure ratios across all stages.
        Each stage is evaluated independently using the calculated pressure ratio, and results are
        assembled into train-level performance metrics.

        Args:
            constraints: Operating constraints including rate, suction pressure, and discharge pressure

        Returns:
            CompressorTrainResultSingleTimeStep: Evaluation results including power consumption,
                inlet/outlet stream conditions, per-stage results, and target pressure status

        Raises:
            IllegalStateException: If stages are missing or contain undefined compressor charts
        """
        # Validate stages are properly prepared before evaluation
        self._validate_stages_prepared()
        assert constraints.suction_pressure is not None
        assert constraints.discharge_pressure is not None
        assert constraints.rate is not None

        pressure_ratios_per_stage = self.calculate_pressure_ratios_per_stage(
            suction_pressure=constraints.suction_pressure, discharge_pressure=constraints.discharge_pressure
        )
        inlet_stream = self.fluid_factory.create_stream_from_standard_rate(
            pressure_bara=constraints.suction_pressure,
            temperature_kelvin=self.stages[0].inlet_temperature_kelvin,
            standard_rate_m3_per_day=constraints.rate,
        )
        if inlet_stream.mass_rate_kg_per_h > 0:
            compressor_stages_result = []
            for stage in self.stages:
                compressor_stage_result = self.calculate_compressor_stage_work_given_outlet_pressure(
                    inlet_stream=inlet_stream,
                    pressure_ratio=pressure_ratios_per_stage,  # type: ignore[arg-type]
                    stage=stage,
                )

                compressor_stages_result.append(compressor_stage_result)
                inlet_stream = compressor_stage_result.outlet_stream

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
        inlet_stream: FluidStream,
        pressure_ratio: float,
        stage: CompressorTrainStage,
        adjust_for_chart: bool = True,
    ) -> CompressorTrainStageResultSingleTimeStep:
        outlet_pressure = inlet_stream.pressure_bara * pressure_ratio

        inlet_stream = inlet_stream.create_stream_with_new_conditions(
            conditions=ProcessConditions(
                pressure_bara=inlet_stream.pressure_bara,
                temperature_kelvin=stage.inlet_temperature_kelvin,
            )
        )

        # To avoid passing empty arrays down to the enthalpy calculation.
        if inlet_stream.mass_rate_kg_per_h > 0:
            polytropic_enthalpy_change_joule_per_kg, polytropic_efficiency = calculate_enthalpy_change_head_iteration(
                inlet_streams=inlet_stream,
                outlet_pressure=outlet_pressure,
                polytropic_efficiency_vs_rate_and_head_function=stage.compressor_chart.efficiency_as_function_of_rate_and_head,
            )

            # Chart corrections to rate and head
            if adjust_for_chart:
                head_joule_per_kg = polytropic_enthalpy_change_joule_per_kg * polytropic_efficiency
                compressor_chart_result = stage.compressor_chart.evaluate_capacity_and_extrapolate_below_minimum(
                    actual_volume_rates=inlet_stream.volumetric_rate,
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
                asv_corrected_actual_rate_m3_per_hour = inlet_stream.volumetric_rate
                mass_rate_to_use_kg_per_hour = inlet_stream.mass_rate_kg_per_h
                rate_has_recirc = False
                pressure_is_choked = False
                rate_exceeds_maximum = False
                head_exceeds_maximum = False
                exceeds_capacity = False

        else:
            polytropic_enthalpy_change_to_use_joule_per_kg = 0.0
            polytropic_enthalpy_change_joule_per_kg = 0.0
            polytropic_efficiency = np.nan
            asv_corrected_actual_rate_m3_per_hour = inlet_stream.volumetric_rate
            mass_rate_to_use_kg_per_hour = inlet_stream.mass_rate_kg_per_h
            rate_has_recirc = False
            pressure_is_choked = False
            rate_exceeds_maximum = False
            head_exceeds_maximum = False
            exceeds_capacity = False

        outlet_stream = inlet_stream.create_stream_with_new_pressure_and_enthalpy_change(
            pressure_bara=outlet_pressure,
            enthalpy_change_joule_per_kg=polytropic_enthalpy_change_to_use_joule_per_kg,  # type: ignore[arg-type]
        )

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
            inlet_stream=inlet_stream,
            outlet_stream=outlet_stream,
            inlet_stream_including_asv=FluidStream(
                thermo_system=inlet_stream.thermo_system,
                mass_rate_kg_per_h=mass_rate_to_use_kg_per_hour,
            ),
            outlet_stream_including_asv=FluidStream(
                thermo_system=outlet_stream.thermo_system,
                mass_rate_kg_per_h=mass_rate_to_use_kg_per_hour,
            ),
            power_megawatt=power_mw,  # type: ignore[arg-type]
            chart_area_flag=chart_area_flag,
            polytropic_enthalpy_change_kJ_per_kg=polytropic_enthalpy_change_to_use_joule_per_kg / 1000,  # type: ignore[arg-type]
            polytropic_enthalpy_change_before_choke_kJ_per_kg=polytropic_enthalpy_change_kilo_joule_per_kg,  # type: ignore[arg-type]
            polytropic_head_kJ_per_kg=(polytropic_enthalpy_change_to_use_joule_per_kg * polytropic_efficiency) / 1000,  # type: ignore[arg-type]
            polytropic_efficiency=polytropic_efficiency,  # type: ignore[arg-type]
            rate_has_recirculation=rate_has_recirc,
            rate_exceeds_maximum=rate_exceeds_maximum,
            pressure_is_choked=pressure_is_choked,
            head_exceeds_maximum=head_exceeds_maximum,
            # Assuming choking and ASV. Valid points are to the left and below the compressor chart.
            point_is_valid=~np.isnan(power_mw),  # type: ignore[arg-type] # power_mw is set to np.NaN if invalid step.
        )


class CompressorTrainSimplifiedKnownStages(CompressorTrainSimplified):
    """A simplified compressor train with a predefined number of stages.

    This model represents a compressor train where the number and configuration of stages
    are known at initialization. Each stage can have different configurations such as inlet
    temperatures and compressor charts.

    The model supports stages with both predefined compressor charts and undefined charts
    that will be generated based on operating data. Stages must have valid compressor charts
    before evaluation can proceed.

    Args:
        fluid_factory: Factory for creating fluid streams
        energy_usage_adjustment_constant: Constant adjustment to energy usage
        energy_usage_adjustment_factor: Factor adjustment to energy usage
        stages: List of compressor stage configurations
        calculate_max_rate: Whether to calculate maximum rates during evaluation
        maximum_power: Optional maximum power constraint
    """

    def __init__(
        self,
        fluid_factory: FluidFactoryInterface,
        energy_usage_adjustment_constant: float,
        energy_usage_adjustment_factor: float,
        stages: list[CompressorStage],
        calculate_max_rate: bool = False,
        maximum_power: float | None = None,
    ):
        logger.debug(f"Creating CompressorTrainSimplifiedKnownStages with n_stages: {len(stages)}")

        # Store original DTO stages for builder usage
        self._original_dto_stages = stages

        stages_mapped = [map_compressor_train_stage_to_domain(stage_dto) for stage_dto in stages]
        super().__init__(
            fluid_factory=fluid_factory,
            energy_usage_adjustment_constant=energy_usage_adjustment_constant,
            energy_usage_adjustment_factor=energy_usage_adjustment_factor,
            stages=stages_mapped,
            typ=EnergyModelType.COMPRESSOR_TRAIN_SIMPLIFIED_WITH_KNOWN_STAGES,
            maximum_power=maximum_power,
            pressure_control=None,  # Not relevant for simplified trains.
            calculate_max_rate=calculate_max_rate,
        )

    def _get_max_std_rate_single_timestep(
        self,
        constraints: CompressorTrainEvaluationInput,
    ) -> float:
        """Calculate the maximum standard rate for a single set of suction and discharge pressures.

        This method determines the maximum rate by evaluating the compressor train's capacity
        based on the given suction and discharge pressures. It considers the compressor's
        operational constraints, including the maximum allowable power and the compressor chart limits.

        Args:
            constraints (CompressorTrainEvaluationInput): The input constraints for the compressor train evaluation,

        Returns:
            float: The maximum standard volume rate in Sm3/day. Returns NaN if the calculation fails.
        """
        suction_pressure = constraints.suction_pressure
        discharge_pressure = constraints.discharge_pressure

        if self.stages is None:
            raise ValueError("Can't calculate max pressure when compressor stages are not defined.")

        use_stage_for_maximum_rate_calculation = [stage.compressor_chart is not None for stage in self.stages]
        if not any(use_stage_for_maximum_rate_calculation):
            logger.error("Calculating maximum rate is not possible when all compressor charts are generic from data")
            return float("nan")

        pressure_ratios_per_stage = self.calculate_pressure_ratios_per_stage(
            suction_pressure=suction_pressure,  # type: ignore[arg-type]
            discharge_pressure=discharge_pressure,  # type: ignore[arg-type]
        )
        inlet_pressure_all_stages = self._calculate_inlet_pressure_stages(
            inlet_pressure=suction_pressure,  # type: ignore[arg-type]
            pressure_ratio_per_stage=pressure_ratios_per_stage,  # type: ignore[arg-type]
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
                inlet_stream=self.fluid_factory.create_stream_from_mass_rate(
                    pressure_bara=inlet_pressure_stages_to_use[stage_number],
                    temperature_kelvin=inlet_temperatures_kelvin_to_use[stage_number],
                    mass_rate_kg_per_h=1,
                ),
                compressor_chart=chart,  # type: ignore[arg-type]
                pressure_ratio=pressure_ratios_per_stage,  # type: ignore[arg-type]
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
        pressure_ratio: float,
        inlet_stream: FluidStream,
        compressor_chart: VariableSpeedCompressorChart,
    ) -> float:
        """Calculate the maximum standard rate for a single set of inputs."""
        outlet_pressure = inlet_stream.pressure_bara * pressure_ratio

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
                    heads=polytropic_head,  # type: ignore[arg-type]
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
                molar_mass=inlet_stream.molar_mass,
                pressure_ratios=pressure_ratio,
                temperatures_kelvin=inlet_stream.temperature_kelvin,
            )
            enthalpy_change_joule_per_kg = polytropic_head / polytropic_efficiency

            outlet_stream = inlet_stream.create_stream_with_new_pressure_and_enthalpy_change(
                pressure_bara=outlet_pressure, enthalpy_change_joule_per_kg=enthalpy_change_joule_per_kg
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
                    f" inlet_pressure: {inlet_stream.pressure_bara}"
                    f" pressure_ratio: {pressure_ratio}."
                    f" inlet_temperature_kelvin: {inlet_stream.temperature_kelvin}."
                    f" molar_mass: {inlet_stream.molar_mass}."
                    f" Final difference between target and results was {diff},"
                    f" while the convergence criterion is set to difference lower than {expected_diff}"
                    f" NOTE! We will use the closest result we got for further calculations."
                    " This should normally not happen. Please contact eCalc support."
                )

        inlet_density_kg_per_m3 = inlet_stream.density
        maximum_mass_rate_kg_per_hour = maximum_actual_volume_rate * inlet_density_kg_per_m3
        maximum_standard_rate = (
            maximum_mass_rate_kg_per_hour
            / inlet_stream.standard_density_gas_phase_after_flash
            * UnitConstants.HOURS_PER_DAY
        )

        return maximum_standard_rate


class CompressorTrainSimplifiedUnknownStages(CompressorTrainSimplified):
    """A simplified compressor train where the number of stages is determined dynamically.

    This model determines the required number of compressor stages based on operating pressure
    ratios and a maximum allowable pressure ratio per stage. The number of stages is calculated
    as the minimum needed to ensure no individual stage exceeds the specified maximum pressure ratio.

    All stages are created from a single template configuration, ensuring consistent inlet
    temperatures and stage properties across the train. Each stage receives an individually
    generated compressor chart based on its operating conditions.

    The stage count is calculated as: ceil(log(max_pressure_ratio) / log(max_pressure_ratio_per_stage))

    Args:
        fluid_factory: Factory for creating fluid streams
        energy_usage_adjustment_constant: Constant adjustment to energy usage
        energy_usage_adjustment_factor: Factor adjustment to energy usage
        stage: Template configuration used for all stages
        maximum_pressure_ratio_per_stage: Maximum allowable pressure ratio per individual stage
        calculate_max_rate: Whether to calculate maximum rates during evaluation
        maximum_power: Optional maximum power constraint
    """

    def __init__(
        self,
        fluid_factory: FluidFactoryInterface,
        energy_usage_adjustment_constant: float,
        energy_usage_adjustment_factor: float,
        stage: CompressorStage,
        maximum_pressure_ratio_per_stage: float,
        calculate_max_rate: bool = False,
        maximum_power: float | None = None,
    ):
        logger.debug("Creating CompressorTrainSimplifiedUnknownStages")

        super().__init__(
            fluid_factory=fluid_factory,
            energy_usage_adjustment_constant=energy_usage_adjustment_constant,
            energy_usage_adjustment_factor=energy_usage_adjustment_factor,
            stages=[],  # Stages are not defined yet
            typ=EnergyModelType.COMPRESSOR_TRAIN_SIMPLIFIED_WITH_UNKNOWN_STAGES,
            maximum_power=maximum_power,
            pressure_control=None,  # Not relevant for simplified trains.
            calculate_max_rate=calculate_max_rate,
        )
        self.stage = stage
        self.maximum_pressure_ratio_per_stage = maximum_pressure_ratio_per_stage
        self._validate_maximum_pressure_ratio_per_stage()

    @staticmethod
    def _calculate_number_of_compressors_needed(
        total_maximum_pressure_ratio: float,
        compressor_maximum_pressure_ratio: float,
    ) -> int:
        """Calculate min number of compressors given a maximum pressure ratio per compressor (default 3.5)."""
        x = math.log(total_maximum_pressure_ratio) / math.log(compressor_maximum_pressure_ratio)
        return math.ceil(x)

    def _get_max_std_rate_single_timestep(
        self,
        constraints: CompressorTrainEvaluationInput,
    ) -> float:
        """Max rate does not have a meaning when using unknown compressor stages."""
        return np.nan

    def _validate_maximum_pressure_ratio_per_stage(self):
        # TODO: Change validation to be > 1.0 instead of >= 0.0. Breaking.
        if self.maximum_pressure_ratio_per_stage < 0:
            msg = f"maximum_pressure_ratio_per_stage must be greater than or equal to 0. Invalid value: {self.maximum_pressure_ratio_per_stage}"

            raise ProcessPressureRatioValidationException(message=str(msg))
