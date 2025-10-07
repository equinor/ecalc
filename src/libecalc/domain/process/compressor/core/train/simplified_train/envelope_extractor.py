from __future__ import annotations

import numpy as np

from libecalc.domain.infrastructure.energy_components.legacy_consumer.system.operational_setting import (
    ConsumerSystemOperationalSettingExpressions,
)
from libecalc.domain.process.compressor.core.train.simplified_train.exceptions import EmptyEnvelopeException
from libecalc.domain.process.compressor.core.train.simplified_train.simplified_train_builder import (
    CompressorOperationalTimeSeries,
)


class EnvelopeExtractor:
    """Service for extracting operational envelopes from compressor system operational settings.

    This service analyzes all operational settings and combines time series data
    to create envelopes that cover all operating scenarios.
    """

    def extract_envelope_for_model_reference(
        self,
        operational_settings: list[ConsumerSystemOperationalSettingExpressions],
        compressor_indices: list[int],
        model_reference_for_error_context: str = "unknown",
    ) -> CompressorOperationalTimeSeries:
        """Extract combined envelope for all trains referencing the same compressor model.

        When multiple trains point to the same COMPRESSOR_MODEL, they are identical and must
        share a combined operational envelope. This ensures all identical trains use the same
        stages that work for all operating conditions any of them encounter.

        Args:
            operational_settings: All operational settings in the compressor system
            compressor_indices: List of train indices that all reference the same model
            model_reference_for_error_context: Model reference name for error context (default: "unknown")

        Returns:
            CompressorOperationalTimeSeries with concatenated arrays from all specified trains across all settings

        Raises:
            ValueError: If operational_settings or compressor_indices is empty, or index out of bounds (programming errors)
            EmptyEnvelopeException: If no valid data found across all operational settings (user configuration error)

        Example:
            Trains at indices [0, 1] both use 'export_compressor_reference':
            - Setting 1: train0=(rate=1000, suction=20, discharge=100), train1=(rate=800, suction=25, discharge=120)
            - Setting 2: train0=(rate=1200, suction=22, discharge=110), train1=(rate=900, suction=27, discharge=130)
            Result: Combined envelope = [(1000,20,100), (800,25,120), (1200,22,110), (900,27,130)]
        """
        if not operational_settings:
            # Not user-facing error: Internal guard, caller must provide settings
            raise ValueError("operational_settings list is empty")

        if not compressor_indices:
            # Not user-facing error: Internal guard, caller must provide indices
            raise ValueError("compressor_indices list is empty")

        all_rates = []
        all_suction = []
        all_discharge = []

        # Iterate over all operational settings
        for setting in operational_settings:
            # For each setting, extract data from ALL trains that share the same model reference
            for compressor_index in compressor_indices:
                # Validate index is within bounds
                # Not user-facing error: Should be prevented by YAML validation
                # (YamlEnergyUsageModelCompressorSystem.validate_operational_settings_match_compressors)
                # This is a defensive guard for internal consistency
                if compressor_index >= setting.number_of_consumers:
                    raise ValueError(
                        f"Compressor index {compressor_index} out of bounds for operational setting "
                        f"with {setting.number_of_consumers} consumers"
                    )

                filtered_data = self._extract_and_filter_operational_data(setting, compressor_index)
                if filtered_data is not None:
                    rates, suction, discharge = filtered_data
                    all_rates.append(rates)
                    all_suction.append(suction)
                    all_discharge.append(discharge)

        if not all_rates:
            # No valid data is a user configuration error - they have invalid expressions or data
            raise EmptyEnvelopeException(
                model_reference=model_reference_for_error_context,
                compressor_indices=compressor_indices,
            )

        # Create time series from concatenated arrays
        # Arrays are guaranteed to have matching lengths due to filtering in helper method
        return CompressorOperationalTimeSeries(
            rates=np.concatenate(all_rates),
            suction_pressures=np.concatenate(all_suction),
            discharge_pressures=np.concatenate(all_discharge),
        )

    def _extract_and_filter_operational_data(
        self,
        setting: ConsumerSystemOperationalSettingExpressions,
        compressor_index: int,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
        """Extract and filter operational data for a single train from a single setting.

        Args:
            setting: Operational setting containing time series data
            compressor_index: Index of the train to extract data for

        Returns:
            Tuple of (rates, suction_pressure, discharge_pressure) arrays if valid data exists, None otherwise
            All returned arrays are guaranteed to have the same length.
        """
        # Extract time series data for this train from this setting
        rates = np.asarray(setting.rates[compressor_index].get_stream_day_values(), dtype=np.float64)
        suction = np.asarray(setting.suction_pressures[compressor_index].get_values(), dtype=np.float64)
        discharge = np.asarray(setting.discharge_pressures[compressor_index].get_values(), dtype=np.float64)

        # Ensure arrays have same length
        min_length = min(len(rates), len(suction), len(discharge))
        rates = rates[:min_length]
        suction = suction[:min_length]
        discharge = discharge[:min_length]

        # Filter NaN (from expression evaluation or masked values) and zero/negative pressures
        valid_mask = ~(np.isnan(rates) | np.isnan(suction) | np.isnan(discharge))
        valid_mask &= suction > 0.0
        valid_mask &= discharge > 0.0

        if np.any(valid_mask):
            return rates[valid_mask], suction[valid_mask], discharge[valid_mask]

        return None
