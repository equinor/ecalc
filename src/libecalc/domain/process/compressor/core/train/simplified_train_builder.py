import math

import numpy as np
from numpy.typing import NDArray

from libecalc.domain.process.compressor.core.train.stage import CompressorTrainStage, UndefinedCompressorStage
from libecalc.domain.process.compressor.core.train.utils.enthalpy_calculations import (
    calculate_enthalpy_change_head_iteration,
)
from libecalc.domain.process.value_objects.chart.compressor.chart_creator import CompressorChartCreator
from libecalc.domain.process.value_objects.fluid_stream.fluid_factory import FluidFactoryInterface


class SimplifiedTrainBuilder:
    """Builder for creating SimplifiedCompressorTrain models with pre-prepared stages.

    This class extracts stage preparation logic from the domain models to enable
    time-unaware domain design. Stages are calculated from time series data
    during model creation, not evaluation.
    """

    def __init__(self, fluid_factory: FluidFactoryInterface):
        self.fluid_factory = fluid_factory

    def prepare_stages_for_simplified_model(
        self,
        stage_template: CompressorTrainStage,
        maximum_pressure_ratio_per_stage: float,
        time_series_data: dict[str, NDArray[np.float64]],
    ) -> list[CompressorTrainStage]:
        """Prepare stages for unknown stages simplified model from time series data.

        Args:
            stage_template: Template stage for unknown stages model
            maximum_pressure_ratio_per_stage: Maximum pressure ratio per stage
            time_series_data: Dictionary containing 'rates', 'suction', 'discharge' arrays

        Returns:
            List of prepared CompressorTrainStage objects with charts
        """
        rates = time_series_data["rates"]
        suction_pressure = time_series_data["suction"]
        discharge_pressure = time_series_data["discharge"]

        if len(suction_pressure) == 0:
            return []

        # Calculate number of stages needed based on maximum pressure ratio
        pressure_ratios = discharge_pressure / suction_pressure
        maximum_pressure_ratio = max(pressure_ratios)
        number_of_compressors = self._calculate_number_of_compressors_needed(
            total_maximum_pressure_ratio=maximum_pressure_ratio,
            compressor_maximum_pressure_ratio=maximum_pressure_ratio_per_stage,
        )

        # Create stages with the template
        stages = [stage_template for _ in range(number_of_compressors)]

        # Prepare charts for stages using time series data
        prepared_stages = self._prepare_charts_for_stages(
            stages=stages,
            rates=rates,
            suction_pressure=suction_pressure,
            discharge_pressure=discharge_pressure,
        )

        return prepared_stages

    def prepare_charts_for_known_stages(
        self,
        stages: list[CompressorTrainStage],
        time_series_data: dict[str, NDArray[np.float64]],
    ) -> list[CompressorTrainStage]:
        """Prepare charts for known stages from time series data.

        Args:
            stages: List of predefined stages
            time_series_data: Dictionary containing 'rates', 'suction', 'discharge' arrays

        Returns:
            List of stages with prepared charts
        """
        rates = time_series_data["rates"]
        suction_pressure = time_series_data["suction"]
        discharge_pressure = time_series_data["discharge"]

        return self._prepare_charts_for_stages(
            stages=stages,
            rates=rates,
            suction_pressure=suction_pressure,
            discharge_pressure=discharge_pressure,
        )

    def _prepare_charts_for_stages(
        self,
        stages: list[CompressorTrainStage],
        rates: NDArray[np.float64],
        suction_pressure: NDArray[np.float64],
        discharge_pressure: NDArray[np.float64],
    ) -> list[CompressorTrainStage]:
        """Core logic for preparing charts for stages from time series data.

        This method extracts the chart generation logic from check_for_undefined_stages()
        in the original simplified_train.py implementation.
        """
        pressure_ratios_per_stage = self._calculate_pressure_ratios_per_stage(
            suction_pressure=suction_pressure, discharge_pressure=discharge_pressure, number_of_stages=len(stages)
        )

        stage_inlet_pressure = suction_pressure
        prepared_stages = []

        for stage_number, stage in enumerate(stages):
            inlet_streams = [
                self.fluid_factory.create_stream_from_standard_rate(
                    pressure_bara=inlet_pressure,
                    temperature_kelvin=stage.inlet_temperature_kelvin,
                    standard_rate_m3_per_day=inlet_rate,
                )
                for inlet_rate, inlet_pressure in zip(rates, stage_inlet_pressure)
            ]
            stage_outlet_pressure = np.multiply(stage_inlet_pressure, pressure_ratios_per_stage)

            if isinstance(stage, UndefinedCompressorStage):
                # Static efficiency regardless of rate and head
                def efficiency_as_function_of_rate_and_head(rates, heads):
                    return np.full_like(rates, fill_value=stage.polytropic_efficiency, dtype=float)

                polytropic_enthalpy_change_joule_per_kg, polytropic_efficiency = (
                    calculate_enthalpy_change_head_iteration(
                        inlet_streams=inlet_streams,
                        outlet_pressure=stage_outlet_pressure,
                        polytropic_efficiency_vs_rate_and_head_function=efficiency_as_function_of_rate_and_head,
                    )
                )

                head_joule_per_kg = polytropic_enthalpy_change_joule_per_kg * polytropic_efficiency
                inlet_actual_rate_m3_per_hour = np.asarray([stream.volumetric_rate for stream in inlet_streams])

                prepared_stage = CompressorTrainStage(
                    compressor_chart=CompressorChartCreator.from_rate_and_head_values(
                        actual_volume_rates_m3_per_hour=inlet_actual_rate_m3_per_hour.tolist(),
                        heads_joule_per_kg=head_joule_per_kg.tolist()
                        if hasattr(head_joule_per_kg, "tolist")
                        else [float(head_joule_per_kg)],
                        polytropic_efficiency=stage.polytropic_efficiency,
                    ),
                    inlet_temperature_kelvin=stage.inlet_temperature_kelvin,
                    remove_liquid_after_cooling=stage.remove_liquid_after_cooling,
                    pressure_drop_ahead_of_stage=stage.pressure_drop_ahead_of_stage,
                )
                prepared_stages.append(prepared_stage)
            else:
                # Stage already has a defined chart, use as-is
                prepared_stages.append(stage)

            # Update inlet pressure for next stage - using working implementation
            stage_inlet_pressure = stage_inlet_pressure * pressure_ratios_per_stage

        return prepared_stages

    @staticmethod
    def _calculate_number_of_compressors_needed(
        total_maximum_pressure_ratio: float,
        compressor_maximum_pressure_ratio: float,
    ) -> int:
        """Calculate min number of compressors given a maximum pressure ratio per compressor."""
        x = math.log(total_maximum_pressure_ratio) / math.log(compressor_maximum_pressure_ratio)
        return math.ceil(x)

    @staticmethod
    def _calculate_pressure_ratios_per_stage(
        suction_pressure: NDArray[np.float64],
        discharge_pressure: NDArray[np.float64],
        number_of_stages: int,
    ) -> NDArray[np.float64]:
        """Calculate pressure ratio per stage for simplified train.

        Returns an array of pressure ratios, one for each timestep.
        Each stage applies the same pressure ratio across all timesteps.
        """
        if number_of_stages == 0:
            return np.ones_like(suction_pressure)

        pressure_ratios = np.divide(
            discharge_pressure, suction_pressure, out=np.ones_like(suction_pressure), where=suction_pressure != 0
        )
        return pressure_ratios ** (1.0 / number_of_stages)
