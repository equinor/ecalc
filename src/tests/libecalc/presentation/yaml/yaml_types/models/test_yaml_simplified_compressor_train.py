import pytest
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_stages import (
    YamlCompressorStage,
    YamlCompressorStages,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_trains import (
    YamlCompatibleTrainsControlMargin,
    YamlSimplifiedVariableSpeedCompressorTrain,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_enums import YamlModelType


def test_control_margin_not_allowed():
    stage = YamlCompressorStage(
        compressor_chart="compressor_chart1",
        inlet_temperature=25,
        control_margin=10,
    )

    stages = YamlCompressorStages(stages=[stage])

    with pytest.raises(ValueError) as exc:
        YamlSimplifiedVariableSpeedCompressorTrain(
            name="simplified_train1",
            type=YamlModelType.SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN,
            compressor_train=stages,
            fluid_model="fluid_model1",
        )

    assert (
        f"simplified_train1: {EcalcYamlKeywords.models_type_compressor_train_stage_control_margin} "
        f"is not allowed for {EcalcYamlKeywords.models_type_compressor_train_simplified}. "
        f"{EcalcYamlKeywords.models_type_compressor_train_stage_control_margin} is only "
        f"supported for the following train-types: "
        f"{', '.join(YamlCompatibleTrainsControlMargin)}"
    ) in str(exc.value)
