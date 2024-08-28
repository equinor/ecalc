from io import StringIO

import pytest

from libecalc.presentation.yaml.validation_errors import DtoValidationError
from libecalc.presentation.yaml.yaml_entities import ResourceStream
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords
from libecalc.presentation.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel
from libecalc.presentation.yaml.yaml_validation_context import (
    YamlModelValidationContextNames,
)


@pytest.fixture
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


def test_control_margin_and_pressure_drop_not_allowed(yaml_resource_with_control_margin_and_pressure_drop):
    with pytest.raises(DtoValidationError) as exc_info:
        PyYamlYamlModel.read(yaml_resource_with_control_margin_and_pressure_drop).validate(
            {
                YamlModelValidationContextNames.resource_file_names: [],
            }
        )

    errors = exc_info.value.errors()

    # Control margin is not allowed:
    error_1 = str(errors[1])

    assert (
        f"MODELS[0].{EcalcYamlKeywords.models_type_compressor_train_simplified}.COMPRESSOR_TRAIN.YamlCompressorStages[YamlCompressorStage].STAGES[0].{EcalcYamlKeywords.models_type_compressor_train_stage_control_margin}"
        in error_1
    )
    assert "This is not a valid keyword" in error_1

    # Control margin unit is not allowed:
    error_2 = str(errors[2])

    assert (
        f"MODELS[0].{EcalcYamlKeywords.models_type_compressor_train_simplified}.COMPRESSOR_TRAIN.YamlCompressorStages[YamlCompressorStage].STAGES[0].{EcalcYamlKeywords.models_type_compressor_train_stage_control_margin_unit}"
        in error_2
    )
    assert "This is not a valid keyword" in error_2

    # Pressure drop ahead of stage is not allowed:
    error_3 = str(errors[3])

    assert (
        f"MODELS[0].{EcalcYamlKeywords.models_type_compressor_train_simplified}.COMPRESSOR_TRAIN.YamlCompressorStages[YamlCompressorStage].STAGES[0].{EcalcYamlKeywords.models_type_compressor_train_pressure_drop_ahead_of_stage}"
        in error_3
    )
    assert "This is not a valid keyword" in error_3
