from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

from libecalc.domain.component_validation_error import DomainValidationException
from libecalc.domain.process.compressor.core.train.stage import CompressorTrainStage, UndefinedCompressorStage
from libecalc.domain.process.compressor.core.train.utils.enthalpy_calculations import (
    calculate_enthalpy_change_head_iteration,
)
from libecalc.domain.process.value_objects.chart.compressor.chart_creator import CompressorChartCreator
from libecalc.domain.process.value_objects.fluid_stream.fluid_factory import FluidFactoryInterface


@dataclass(frozen=True)
class CompressorOperationalTimeSeries:
    """Time series data for compressor stage preparation.

    Contains operational data (rates, suction pressure, discharge pressure)
    for all timesteps in a period. Used to prepare simplified compressor train stages.

    Validation is performed in __post_init__ to ensure data integrity.

    Note:
    - Arrays are never filtered by CONDITION - validation_mask is handled separately
    """

    rates: NDArray[np.float64]
    suction_pressures: NDArray[np.float64]
    discharge_pressures: NDArray[np.float64]

    def __post_init__(self):
        """Validate time series data integrity.

        Raises:
            DomainValidationException: If data is empty or arrays have mismatched lengths
        """
        if len(self.rates) == 0:
            raise DomainValidationException(
                "Compressor operational time series data is empty. This indicates no valid timesteps in the period."
            )

        if not (len(self.rates) == len(self.suction_pressures) == len(self.discharge_pressures)):
            raise DomainValidationException(
                f"Time series arrays must have same length: "
                f"rates={len(self.rates)}, "
                f"suction_pressures={len(self.suction_pressures)}, "
                f"discharge_pressures={len(self.discharge_pressures)}"
            )

    @classmethod
    def from_lists(
        cls,
        rates: list[float],
        suction_pressure: list[float],
        discharge_pressure: list[float],
    ) -> CompressorOperationalTimeSeries:
        """Create from Python lists (converts to numpy arrays).

        Args:
            rates: Flow rates [Sm3/day]
            suction_pressure: Suction pressures [bara]
            discharge_pressure: Discharge pressures [bara]

        Returns:
            CompressorOperationalTimeSeries with validated data

        Raises:
            DomainValidationException: If data is empty or arrays have mismatched lengths
        """
        return cls(
            rates=np.asarray(rates, dtype=np.float64),
            suction_pressures=np.asarray(suction_pressure, dtype=np.float64),
            discharge_pressures=np.asarray(discharge_pressure, dtype=np.float64),
        )


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
        time_series_data: CompressorOperationalTimeSeries,
    ) -> list[CompressorTrainStage]:
        """Prepare stages for unknown stages simplified model from time series data.

        Args:
            stage_template: Template stage for unknown stages model
            maximum_pressure_ratio_per_stage: Maximum pressure ratio per stage
            time_series_data: Operational time series data (rates and pressures, validated)

        Returns:
            List of prepared CompressorTrainStage objects with charts
        """
        # Extract arrays - validation already performed in CompressorOperationalTimeSeries
        rates = time_series_data.rates
        suction_pressure = time_series_data.suction_pressures
        discharge_pressure = time_series_data.discharge_pressures

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
        if any(isinstance(stage, UndefinedCompressorStage) for stage in stages):
            return self._prepare_charts_for_stages(
                stages=stages,
                rates=rates,
                suction_pressure=suction_pressure,
                discharge_pressure=discharge_pressure,
            )
        else:
            return stages

    def prepare_charts_for_known_stages(
        self,
        stages: list[CompressorTrainStage],
        time_series_data: CompressorOperationalTimeSeries | None = None,
    ) -> list[CompressorTrainStage]:
        """Prepare charts for known stages from time series data.

        Args:
            stages: List of predefined stages
            time_series_data: Operational time series data (rates and pressures, validated)

        Returns:
            List of stages with prepared charts
        """
        if any(isinstance(stage, UndefinedCompressorStage) for stage in stages):
            assert time_series_data is not None
            # Extract arrays - validation already performed in CompressorOperationalTimeSeries
            rates = time_series_data.rates
            suction_pressure = time_series_data.suction_pressures
            discharge_pressure = time_series_data.discharge_pressures

            return self._prepare_charts_for_stages(
                stages=stages,
                rates=rates,
                suction_pressure=suction_pressure,
                discharge_pressure=discharge_pressure,
            )
        else:
            # No undefined stages, no chart preparation needed
            return stages

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

        for _stage_number, stage in enumerate(stages):
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
                # A stage without a defined compressor chart is 'undefined' ("generic from input" chart artifact)
                undefined_stage: UndefinedCompressorStage = stage

                # Static efficiency regardless of rate and head
                def efficiency_as_function_of_rate_and_head(rates, heads):
                    return np.full_like(rates, fill_value=undefined_stage.polytropic_efficiency, dtype=float)

                polytropic_enthalpy_change_joule_per_kg, polytropic_efficiency = (
                    calculate_enthalpy_change_head_iteration(
                        inlet_streams=inlet_streams,
                        outlet_pressure=stage_outlet_pressure,
                        polytropic_efficiency_vs_rate_and_head_function=efficiency_as_function_of_rate_and_head,
                    )
                )

                head_joule_per_kg = polytropic_enthalpy_change_joule_per_kg * polytropic_efficiency
                inlet_actual_rate_m3_per_hour = np.asarray([stream.volumetric_rate for stream in inlet_streams])

                # Convert numpy arrays to lists for proper type annotation
                actual_rates_list: list[float] = inlet_actual_rate_m3_per_hour.astype(float).tolist()

                # Handle union type for head_joule_per_kg
                if isinstance(head_joule_per_kg, np.ndarray):
                    heads_list: list[float] = head_joule_per_kg.astype(float).tolist()
                else:
                    heads_list = [float(head_joule_per_kg)]

                prepared_stage = CompressorTrainStage(
                    compressor_chart=CompressorChartCreator.from_rate_and_head_values(
                        actual_volume_rates_m3_per_hour=actual_rates_list,
                        heads_joule_per_kg=heads_list,
                        polytropic_efficiency=undefined_stage.polytropic_efficiency,
                    ),
                    inlet_temperature_kelvin=undefined_stage.inlet_temperature_kelvin,
                    remove_liquid_after_cooling=undefined_stage.remove_liquid_after_cooling,
                    pressure_drop_ahead_of_stage=undefined_stage.pressure_drop_ahead_of_stage,
                )
                prepared_stages.append(prepared_stage)
            else:
                # Stage already has a defined chart (generic from design point chart), use as-is
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
