"""Tests for MECHANICAL_EFFICIENCY on all compressor train types."""

import pytest
from pydantic import ValidationError

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


def create_train(train_class, stages, **kwargs):
    """Factory to create any train type with common defaults."""
    type_map = {
        YamlSingleSpeedCompressorTrain: "SINGLE_SPEED_COMPRESSOR_TRAIN",
        YamlVariableSpeedCompressorTrain: "VARIABLE_SPEED_COMPRESSOR_TRAIN",
        YamlSimplifiedVariableSpeedCompressorTrain: "SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN",
    }
    return train_class(
        name="test_train",
        type=type_map[train_class],
        compressor_train=stages,
        fluid_model="fluid_ref",
        **kwargs,
    )


class TestMechanicalEfficiencyValidation:
    """Tests for MECHANICAL_EFFICIENCY field validation across all train types."""

    @pytest.mark.parametrize(
        "train_class,stages_fixture",
        [
            (YamlSingleSpeedCompressorTrain, "common_shaft_stages"),
            (YamlVariableSpeedCompressorTrain, "common_shaft_stages"),
            (YamlSimplifiedVariableSpeedCompressorTrain, "simplified_stages"),
        ],
    )
    def test_valid_mechanical_efficiency(self, train_class, stages_fixture, request):
        """Valid mechanical efficiency within range (0, 1]."""
        stages = request.getfixturevalue(stages_fixture)
        train = create_train(train_class, stages, mechanical_efficiency=0.95)
        assert train.mechanical_efficiency == 0.95

    @pytest.mark.parametrize(
        "train_class,stages_fixture",
        [
            (YamlSingleSpeedCompressorTrain, "common_shaft_stages"),
            (YamlVariableSpeedCompressorTrain, "common_shaft_stages"),
            (YamlSimplifiedVariableSpeedCompressorTrain, "simplified_stages"),
        ],
    )
    def test_default_mechanical_efficiency(self, train_class, stages_fixture, request):
        """Default mechanical efficiency is 1.0 (no losses)."""
        stages = request.getfixturevalue(stages_fixture)
        train = create_train(train_class, stages)
        assert train.mechanical_efficiency == 1.0

    @pytest.mark.parametrize(
        "train_class,stages_fixture",
        [
            (YamlSingleSpeedCompressorTrain, "common_shaft_stages"),
            (YamlVariableSpeedCompressorTrain, "common_shaft_stages"),
            (YamlSimplifiedVariableSpeedCompressorTrain, "simplified_stages"),
        ],
    )
    @pytest.mark.parametrize("invalid_value", [0.0, -0.1, 1.1])
    def test_invalid_mechanical_efficiency(self, train_class, stages_fixture, invalid_value, request):
        """Invalid mechanical efficiency values should fail validation."""
        stages = request.getfixturevalue(stages_fixture)
        with pytest.raises(ValidationError):
            create_train(train_class, stages, mechanical_efficiency=invalid_value)


class TestMutualExclusivityWithLegacyParams:
    """Tests that MECHANICAL_EFFICIENCY cannot be used with legacy POWER_ADJUSTMENT_* params."""

    @pytest.mark.parametrize(
        "train_class,stages_fixture",
        [
            (YamlSingleSpeedCompressorTrain, "common_shaft_stages"),
            (YamlVariableSpeedCompressorTrain, "common_shaft_stages"),
            (YamlSimplifiedVariableSpeedCompressorTrain, "simplified_stages"),
        ],
    )
    def test_cannot_combine_with_power_adjustment_factor(self, train_class, stages_fixture, request):
        """Cannot use both MECHANICAL_EFFICIENCY and POWER_ADJUSTMENT_FACTOR."""
        stages = request.getfixturevalue(stages_fixture)
        with pytest.raises(ValidationError) as exc_info:
            create_train(train_class, stages, mechanical_efficiency=0.95, power_adjustment_factor=1.05)
        assert "cannot" in str(exc_info.value).lower()

    @pytest.mark.parametrize(
        "train_class,stages_fixture",
        [
            (YamlSingleSpeedCompressorTrain, "common_shaft_stages"),
            (YamlVariableSpeedCompressorTrain, "common_shaft_stages"),
            (YamlSimplifiedVariableSpeedCompressorTrain, "simplified_stages"),
        ],
    )
    def test_cannot_combine_with_power_adjustment_constant(self, train_class, stages_fixture, request):
        """Cannot use both MECHANICAL_EFFICIENCY and POWER_ADJUSTMENT_CONSTANT."""
        stages = request.getfixturevalue(stages_fixture)
        with pytest.raises(ValidationError) as exc_info:
            create_train(train_class, stages, mechanical_efficiency=0.95, power_adjustment_constant=1.0)
        assert "cannot" in str(exc_info.value).lower()
