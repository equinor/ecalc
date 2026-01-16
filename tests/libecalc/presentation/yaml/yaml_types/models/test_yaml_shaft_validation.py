"""Tests for shaft single-usage validation and compressor train shaft references."""

import pytest
from pydantic import ValidationError

from libecalc.common.errors.exceptions import EcalcError
from libecalc.presentation.yaml.yaml_reference_service import _validate_shaft_single_usage
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_stages import (
    YamlCompressorStage,
    YamlCompressorStageWithMarginAndPressureDrop,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_trains import (
    YamlCompressorStages,
    YamlSimplifiedVariableSpeedCompressorTrain,
    YamlSingleSpeedCompressorTrain,
    YamlVariableSpeedCompressorTrain,
)


@pytest.fixture
def common_shaft_stages():
    """Minimal stages for single/variable speed trains."""
    stage = YamlCompressorStageWithMarginAndPressureDrop(
        compressor_chart="chart_ref",
        inlet_temperature=30.0,
        control_margin=0.0,
        control_margin_unit="PERCENTAGE",
    )
    return YamlCompressorStages(stages=[stage])


@pytest.fixture
def simplified_stages():
    """Minimal stages for simplified trains."""
    return YamlCompressorStages[YamlCompressorStage](
        stages=[YamlCompressorStage(inlet_temperature=30, compressor_chart="chart_ref")],
    )


def create_single_speed_train(stages, **kwargs):
    """Factory for single speed train with defaults."""
    return YamlSingleSpeedCompressorTrain(
        name=kwargs.pop("name", "test_train"),
        type="SINGLE_SPEED_COMPRESSOR_TRAIN",
        compressor_train=stages,
        fluid_model="fluid_ref",
        **kwargs,
    )


def create_variable_speed_train(stages, **kwargs):
    """Factory for variable speed train with defaults."""
    return YamlVariableSpeedCompressorTrain(
        name=kwargs.pop("name", "test_train"),
        type="VARIABLE_SPEED_COMPRESSOR_TRAIN",
        compressor_train=stages,
        fluid_model="fluid_ref",
        **kwargs,
    )


def create_simplified_train(stages, **kwargs):
    """Factory for simplified train with defaults."""
    return YamlSimplifiedVariableSpeedCompressorTrain(
        name=kwargs.pop("name", "test_train"),
        type="SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN",
        compressor_train=stages,
        fluid_model="fluid_ref",
        **kwargs,
    )


class TestShaftSingleUsageValidation:
    """Test that shafts can only be used by one compressor train."""

    def test_different_shafts_allowed(self, common_shaft_stages):
        """Multiple trains with different shafts should pass validation."""
        train1 = create_single_speed_train(common_shaft_stages, name="train1", shaft="shaft1")
        train2 = create_variable_speed_train(common_shaft_stages, name="train2", shaft="shaft2")
        _validate_shaft_single_usage([train1, train2])  # Should not raise

    def test_same_shaft_disallowed(self, common_shaft_stages):
        """Two trains referencing the same shaft should fail validation."""
        train1 = create_single_speed_train(common_shaft_stages, name="train1", shaft="shared_shaft")
        train2 = create_variable_speed_train(common_shaft_stages, name="train2", shaft="shared_shaft")

        with pytest.raises(EcalcError, match="shared_shaft.*already used by train 'train1'"):
            _validate_shaft_single_usage([train1, train2])

    def test_trains_without_shaft_allowed(self, common_shaft_stages):
        """Trains without shaft references should pass validation."""
        train1 = create_single_speed_train(common_shaft_stages, name="train1")
        train2 = create_variable_speed_train(common_shaft_stages, name="train2")
        _validate_shaft_single_usage([train1, train2])  # Should not raise

    def test_mixed_shaft_and_no_shaft(self, common_shaft_stages):
        """Mix of trains with and without shaft references should pass."""
        train1 = create_single_speed_train(common_shaft_stages, name="train1", shaft="my_shaft")
        train2 = create_variable_speed_train(common_shaft_stages, name="train2")
        _validate_shaft_single_usage([train1, train2])  # Should not raise


class TestShaftAndLegacyParamsMutualExclusivity:
    """Test that shaft and legacy power adjustment params are mutually exclusive."""

    @pytest.mark.parametrize("legacy_param", ["power_adjustment_factor", "power_adjustment_constant"])
    def test_shaft_with_legacy_param_fails(self, common_shaft_stages, legacy_param):
        """Cannot use both shaft and legacy power adjustment params."""
        kwargs = {"shaft": "my_shaft", legacy_param: 1.1 if "factor" in legacy_param else 0.5}
        with pytest.raises(ValueError, match="Cannot specify both SHAFT and POWER_ADJUSTMENT"):
            create_single_speed_train(common_shaft_stages, **kwargs)


class TestSimplifiedTrainMechanicalEfficiency:
    """Tests for MECHANICAL_EFFICIENCY on simplified compressor trains."""

    def test_mechanical_efficiency_valid(self, simplified_stages):
        """Valid mechanical efficiency within range (0, 1]."""
        train = create_simplified_train(simplified_stages, mechanical_efficiency=0.95)
        assert train.mechanical_efficiency == 0.95

    def test_mechanical_efficiency_default(self, simplified_stages):
        """Default mechanical efficiency is 1.0 (no loss)."""
        train = create_simplified_train(simplified_stages)
        assert train.mechanical_efficiency == 1.0

    @pytest.mark.parametrize("invalid_value", [0.0, -0.1, 1.1])
    def test_mechanical_efficiency_invalid(self, simplified_stages, invalid_value):
        """Invalid mechanical efficiency values should fail."""
        with pytest.raises(ValidationError):
            create_simplified_train(simplified_stages, mechanical_efficiency=invalid_value)


class TestSimplifiedTrainMutualExclusivity:
    """Tests for mutual exclusivity on simplified trains."""

    @pytest.mark.parametrize("legacy_param", ["power_adjustment_factor", "power_adjustment_constant"])
    def test_mechanical_efficiency_with_legacy_param_fails(self, simplified_stages, legacy_param):
        """Cannot use both MECHANICAL_EFFICIENCY and legacy params."""
        kwargs = {"mechanical_efficiency": 0.95, legacy_param: 1.05 if "factor" in legacy_param else 1.0}
        with pytest.raises(ValidationError) as exc_info:
            create_simplified_train(simplified_stages, **kwargs)
        assert "cannot be used together" in str(exc_info.value).lower()
