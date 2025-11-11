"""Tests for YAML validation of consumer systems (compressor and pump systems)."""

import pytest
from pydantic import ValidationError

from libecalc.presentation.yaml.yaml_types.components.legacy.energy_usage_model.yaml_energy_usage_model_consumer_system import (
    YamlCompressorSystemCompressor,
    YamlCompressorSystemOperationalSetting,
    YamlEnergyUsageModelCompressorSystem,
)


class TestCompressorSystemValidation:
    """Test validation of compressor system operational settings."""

    def test_mismatched_rates_raises_validation_error(self):
        """System with mismatched rates array length raises ValidationError."""
        with pytest.raises(ValidationError, match="RATES has 2 values.*but system has 3 compressors"):
            YamlEnergyUsageModelCompressorSystem(
                type="COMPRESSOR_SYSTEM",
                compressors=[
                    YamlCompressorSystemCompressor(name="comp1", compressor_model="model_ref"),
                    YamlCompressorSystemCompressor(name="comp2", compressor_model="model_ref"),
                    YamlCompressorSystemCompressor(name="comp3", compressor_model="model_ref"),
                ],
                operational_settings=[
                    YamlCompressorSystemOperationalSetting(
                        rates=["100", "200"],  # Only 2 rates but 3 compressors
                        suction_pressure="20",
                        discharge_pressure="100",
                    )
                ],
            )

    def test_mismatched_suction_pressures_raises_validation_error(self):
        """System with mismatched suction pressures array length raises ValidationError."""
        with pytest.raises(ValidationError, match="SUCTION_PRESSURES.*but system has 2 compressors"):
            YamlEnergyUsageModelCompressorSystem(
                type="COMPRESSOR_SYSTEM",
                compressors=[
                    YamlCompressorSystemCompressor(name="comp1", compressor_model="model_ref"),
                    YamlCompressorSystemCompressor(name="comp2", compressor_model="model_ref"),
                ],
                operational_settings=[
                    YamlCompressorSystemOperationalSetting(
                        rate_fractions=["0.5", "0.5"],
                        suction_pressures=["20"],  # Only 1 pressure but 2 compressors
                        discharge_pressure="100",
                    )
                ],
                total_system_rate="1000",
            )

    def test_mismatched_discharge_pressures_raises_validation_error(self):
        """System with mismatched discharge pressures array length raises ValidationError."""
        with pytest.raises(ValidationError, match="DISCHARGE_PRESSURES has 3 values.*but system has 2 compressors"):
            YamlEnergyUsageModelCompressorSystem(
                type="COMPRESSOR_SYSTEM",
                compressors=[
                    YamlCompressorSystemCompressor(name="comp1", compressor_model="model_ref"),
                    YamlCompressorSystemCompressor(name="comp2", compressor_model="model_ref"),
                ],
                operational_settings=[
                    YamlCompressorSystemOperationalSetting(
                        rates=["100", "200"],
                        suction_pressure="20",
                        discharge_pressures=["100", "120", "140"],  # 3 pressures but 2 compressors
                    )
                ],
            )

    def test_second_operational_setting_identified_in_error(self):
        """Error message identifies which operational setting has wrong array length."""
        with pytest.raises(ValidationError, match="Operational setting 2"):
            YamlEnergyUsageModelCompressorSystem(
                type="COMPRESSOR_SYSTEM",
                compressors=[
                    YamlCompressorSystemCompressor(name="comp1", compressor_model="model_ref"),
                    YamlCompressorSystemCompressor(name="comp2", compressor_model="model_ref"),
                ],
                operational_settings=[
                    YamlCompressorSystemOperationalSetting(
                        rates=["100", "200"],
                        suction_pressure="20",
                        discharge_pressure="100",
                    ),
                    YamlCompressorSystemOperationalSetting(
                        rates=["150"],  # Only 1 rate in second setting
                        suction_pressure="22",
                        discharge_pressure="110",
                    ),
                ],
            )

    def test_common_pressure_expressions_are_valid(self):
        """Using common suction/discharge pressure (not per-compressor) is valid."""
        system = YamlEnergyUsageModelCompressorSystem(
            type="COMPRESSOR_SYSTEM",
            compressors=[
                YamlCompressorSystemCompressor(name="comp1", compressor_model="model_ref"),
                YamlCompressorSystemCompressor(name="comp2", compressor_model="model_ref"),
            ],
            operational_settings=[
                YamlCompressorSystemOperationalSetting(
                    rates=["100", "200"],
                    suction_pressure="20",  # Common pressure, not per-compressor
                    discharge_pressure="100",  # Common pressure, not per-compressor
                )
            ],
        )
        assert len(system.compressors) == 2
