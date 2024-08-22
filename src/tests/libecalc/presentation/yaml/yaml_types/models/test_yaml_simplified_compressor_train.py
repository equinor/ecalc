from io import StringIO

import pytest
from libecalc.presentation.yaml.validation_errors import DtoValidationError
from libecalc.presentation.yaml.yaml_entities import ResourceStream
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel
from libecalc.presentation.yaml.yaml_validation_context import (
    YamlModelValidationContextNames,
)


def yaml_resource_with_control_margin_and_pressure_drop():
    yaml_with_control_margin_and_pressure_drop = """
    MODELS:
        - NAME: simplified_compressor_train
          TYPE: SIMPLIFIED_VARIABLE_SPEED_COMPRESSOR_TRAIN
          FLUID_MODEL: fluid_model
          COMPRESSOR_TRAIN:
            STAGES:
              - COMPRESSOR_CHART: chart1
                INLET_TEMPERATURE: 30
                CONTROL_MARGIN: 10
                CONTROL_MARGIN_UNIT: PERCENTAGE
                PRESSURE_DROP_AHEAD_OF_STAGE: 2
        """
    return ResourceStream(
        name="yaml_with_control_margin_and_pressure_drop", stream=StringIO(yaml_with_control_margin_and_pressure_drop)
    )


def test_control_margin_and_pressure_drop_not_allowed():
    with pytest.raises(DtoValidationError) as exc_info:
        PyYamlYamlModel.read(yaml_resource_with_control_margin_and_pressure_drop()).validate(
            {
                YamlModelValidationContextNames.resource_file_names: [],
            }
        )

    errors = exc_info.value.errors()

    # Control margin is not allowed:
    assert (
        f"MODELS[0].{EcalcYamlKeywords.models_type_compressor_train_simplified}.COMPRESSOR_TRAIN."
        f"YamlCompressorStages[YamlCompressorStage].STAGES[0]."
        f"{EcalcYamlKeywords.models_type_compressor_train_stage_control_margin}:	"
        f"This is not a valid keyword"
    ) in str(errors[1])

    # Control margin unit is not allowed:
    assert (
        f"MODELS[0].{EcalcYamlKeywords.models_type_compressor_train_simplified}.COMPRESSOR_TRAIN."
        f"YamlCompressorStages[YamlCompressorStage].STAGES[0]."
        f"{EcalcYamlKeywords.models_type_compressor_train_stage_control_margin_unit}:	"
        f"This is not a valid keyword"
    ) in str(errors[2])

    # Pressure drop ahead of stage is not allowed:
    assert (
        f"MODELS[0].{EcalcYamlKeywords.models_type_compressor_train_simplified}.COMPRESSOR_TRAIN."
        f"YamlCompressorStages[YamlCompressorStage].STAGES[0]."
        f"{EcalcYamlKeywords.models_type_compressor_train_pressure_drop_ahead_of_stage}:	"
        f"This is not a valid keyword"
    ) in str(errors[3])
