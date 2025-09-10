"""
SimplifiedTrainBuilder - Extract stage preparation logic from SimplifiedTrain models.

This builder prepares compressor stages upfront using time-series data, enabling
time-unaware domain models that work with pre-calculated stages.
"""

import math

import numpy as np
from numpy.typing import NDArray

from libecalc.common.logger import logger
from libecalc.domain.process.compressor.core.train.stage import CompressorTrainStage, UndefinedCompressorStage
from libecalc.domain.process.compressor.core.train.utils.enthalpy_calculations import (
    calculate_enthalpy_change_head_iteration,
)
from libecalc.domain.process.compressor.core.utils import map_compressor_train_stage_to_domain
from libecalc.domain.process.compressor.dto import CompressorStage
from libecalc.domain.process.value_objects.chart.compressor.chart_creator import CompressorChartCreator
from libecalc.domain.process.value_objects.fluid_stream.fluid_factory import FluidFactoryInterface


class SimplifiedTrainBuilder:
    """Builder for creating simplified compressor trains with pre-prepared stages."""

    def __init__(self, fluid_factory: FluidFactoryInterface):
        self.fluid_factory = fluid_factory

    def prepare_stages_for_known_stages(
        self,
        stages: list[CompressorStage],
        suction_pressure: NDArray[np.float64],
        discharge_pressure: NDArray[np.float64],
        rate: NDArray[np.float64],
    ) -> list[CompressorTrainStage]:
        """Prepare stages for CompressorTrainSimplifiedKnownStages model.

        For known stages, we need to handle any undefined stages (with generic charts)
        by generating their compressor charts from the provided time-series data.
        """
        if len(suction_pressure) == 0:
            logger.warning("No time-series data available for stage preparation")
            return [map_compressor_train_stage_to_domain(stage) for stage in stages]

        # Map DTO stages to domain stages
        domain_stages = [map_compressor_train_stage_to_domain(stage) for stage in stages]

        # Process each stage, generating charts for undefined stages
        prepared_stages = []
        pressure_ratios_per_stage = self._calculate_pressure_ratios_per_stage(
            suction_pressure=suction_pressure,
            discharge_pressure=discharge_pressure,
            number_of_stages=len(domain_stages),
        )

        stage_inlet_pressure = suction_pressure
        for _stage_number, stage in enumerate(domain_stages):
            if isinstance(stage, UndefinedCompressorStage):
                # Generate chart for undefined stage - matching original implementation
                prepared_stage = self._create_stage_with_generated_chart(
                    undefined_stage=stage,
                    inlet_pressure=stage_inlet_pressure,
                    pressure_ratio_per_stage=pressure_ratios_per_stage,
                    rate=rate,
                )
                prepared_stages.append(prepared_stage)
            else:
                # Stage already has a chart, use as-is
                prepared_stages.append(stage)

            # Update inlet pressure for next stage
            stage_inlet_pressure = stage_inlet_pressure * pressure_ratios_per_stage

        return prepared_stages

    def prepare_stages_for_unknown_stages(
        self,
        stage_template: CompressorStage,
        maximum_pressure_ratio_per_stage: float,
        suction_pressure: NDArray[np.float64],
        discharge_pressure: NDArray[np.float64],
        rate: NDArray[np.float64],
    ) -> list[CompressorTrainStage]:
        """Prepare stages for CompressorTrainSimplifiedUnknownStages model.

        Calculate the number of stages needed based on maximum pressure ratio
        and create stages based on the template.
        """
        if len(suction_pressure) == 0:
            logger.warning("No time-series data available for stage preparation")
            return []

        # Calculate number of stages needed
        pressure_ratios = discharge_pressure / suction_pressure
        maximum_pressure_ratio = max(pressure_ratios)
        number_of_stages = self._calculate_number_of_compressors_needed(
            total_maximum_pressure_ratio=maximum_pressure_ratio,
            compressor_maximum_pressure_ratio=maximum_pressure_ratio_per_stage,
        )

        logger.debug(f"Calculated {number_of_stages} stages for maximum pressure ratio {maximum_pressure_ratio}")

        # Create stages from template
        domain_stage_template = map_compressor_train_stage_to_domain(stage_template)
        prepared_stages = []

        # Calculate pressure ratios per stage
        pressure_ratios_per_stage = self._calculate_pressure_ratios_per_stage(
            suction_pressure=suction_pressure, discharge_pressure=discharge_pressure, number_of_stages=number_of_stages
        )

        stage_inlet_pressure = suction_pressure
        for _stage_number in range(number_of_stages):
            if isinstance(domain_stage_template, UndefinedCompressorStage):
                # Generate chart for undefined stage
                prepared_stage = self._create_stage_with_generated_chart(
                    undefined_stage=domain_stage_template,
                    inlet_pressure=stage_inlet_pressure,
                    pressure_ratio_per_stage=pressure_ratios_per_stage,
                    rate=rate,
                )
            else:
                # Use template stage as-is (with existing chart)
                prepared_stage = CompressorTrainStage(
                    compressor_chart=domain_stage_template.compressor_chart,
                    inlet_temperature_kelvin=domain_stage_template.inlet_temperature_kelvin,
                    remove_liquid_after_cooling=domain_stage_template.remove_liquid_after_cooling,
                    pressure_drop_ahead_of_stage=domain_stage_template.pressure_drop_ahead_of_stage,
                )

            prepared_stages.append(prepared_stage)
            # Update inlet pressure for next stage
            stage_inlet_pressure = stage_inlet_pressure * pressure_ratios_per_stage

        return prepared_stages

    def _create_stage_with_generated_chart(
        self,
        undefined_stage: UndefinedCompressorStage,
        inlet_pressure: NDArray[np.float64],
        pressure_ratio_per_stage: NDArray[np.float64],
        rate: NDArray[np.float64],
    ) -> CompressorTrainStage:
        """Create a CompressorTrainStage with generated chart for an undefined stage.

        Generates a compressor chart from time-series rate and thermodynamic data,
        then creates a complete stage with the generated chart.
        """
        stage_outlet_pressure = inlet_pressure * pressure_ratio_per_stage

        # Create inlet streams for all timesteps
        inlet_streams = [
            self.fluid_factory.create_stream_from_standard_rate(
                pressure_bara=inlet_pressure_value,
                temperature_kelvin=undefined_stage.inlet_temperature_kelvin,
                standard_rate_m3_per_day=rate_value,
            )
            for rate_value, inlet_pressure_value in zip(rate, inlet_pressure)
        ]

        # Static efficiency function for undefined stages
        def efficiency_as_function_of_rate_and_head(rates, heads):
            return np.full_like(rates, fill_value=undefined_stage.polytropic_efficiency, dtype=float)

        polytropic_enthalpy_change_joule_per_kg, polytropic_efficiency = calculate_enthalpy_change_head_iteration(
            inlet_streams=inlet_streams,
            outlet_pressure=stage_outlet_pressure,
            polytropic_efficiency_vs_rate_and_head_function=efficiency_as_function_of_rate_and_head,
        )

        head_joule_per_kg = polytropic_enthalpy_change_joule_per_kg * polytropic_efficiency
        inlet_actual_rate_m3_per_hour = np.asarray([stream.volumetric_rate for stream in inlet_streams])

        # Create the compressor chart from calculated data
        compressor_chart = CompressorChartCreator.from_rate_and_head_values(
            actual_volume_rates_m3_per_hour=list(inlet_actual_rate_m3_per_hour),
            heads_joule_per_kg=list(np.asarray(head_joule_per_kg)),
            polytropic_efficiency=undefined_stage.polytropic_efficiency,
        )

        return CompressorTrainStage(
            compressor_chart=compressor_chart,
            inlet_temperature_kelvin=undefined_stage.inlet_temperature_kelvin,
            remove_liquid_after_cooling=undefined_stage.remove_liquid_after_cooling,
            pressure_drop_ahead_of_stage=undefined_stage.pressure_drop_ahead_of_stage,
        )

    @staticmethod
    def _calculate_pressure_ratios_per_stage(
        suction_pressure: NDArray[np.float64],
        discharge_pressure: NDArray[np.float64],
        number_of_stages: int,
    ) -> NDArray[np.float64]:
        """Calculate the pressure ratios per stage for simplified train models.

        Returns an array of pressure ratios, one for each timestep.
        Each stage applies the same pressure ratio across all timesteps.
        """
        if number_of_stages == 0:
            return np.ones_like(suction_pressure)

        pressure_ratios = np.divide(
            discharge_pressure, suction_pressure, out=np.ones_like(suction_pressure), where=suction_pressure != 0
        )
        return pressure_ratios ** (1.0 / number_of_stages)

    @staticmethod
    def _calculate_number_of_compressors_needed(
        total_maximum_pressure_ratio: float,
        compressor_maximum_pressure_ratio: float,
    ) -> int:
        """Calculate minimum number of compressors given a maximum pressure ratio per compressor."""
        x = math.log(total_maximum_pressure_ratio) / math.log(compressor_maximum_pressure_ratio)
        return math.ceil(x)
