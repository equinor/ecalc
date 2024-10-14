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
def yaml_resource_variable_speed_without_control_margin():
    yaml_variable_speed_without_control_margin = """
    MODELS:
        - NAME: variable_speed_compressor_train
          TYPE: VARIABLE_SPEED_COMPRESSOR_TRAIN
          FLUID_MODEL: fluid_model
          COMPRESSOR_TRAIN:
            STAGES:
              - COMPRESSOR_CHART: variable_speed_chart
                INLET_TEMPERATURE: 30
                PRESSURE_DROP_AHEAD_OF_STAGE: 2
        """
    return ResourceStream(
        name="yaml_variable_speed_without_control_margin", stream=StringIO(yaml_variable_speed_without_control_margin)
    )


def test_control_margin_required(yaml_resource_variable_speed_without_control_margin):
    with pytest.raises(DtoValidationError) as exc_info:
        PyYamlYamlModel.read(yaml_resource_variable_speed_without_control_margin).validate(
            {
                YamlModelValidationContextNames.resource_file_names: [],
            }
        )
    errors = exc_info.value.errors()

    # Control margin is required for variable speed compressor train:
    error_1 = str(errors[1])

    assert (
        f"MODELS[0].{EcalcYamlKeywords.models_type_compressor_train_variable_speed}.COMPRESSOR_TRAIN.STAGES[0].{EcalcYamlKeywords.models_type_compressor_train_stage_control_margin}"
        in error_1
    )
    assert "This keyword is missing, it is required" in error_1

    # Control margin unit is required for variable speed compressor train:
    error_2 = str(errors[2])

    assert (
        f"MODELS[0].{EcalcYamlKeywords.models_type_compressor_train_variable_speed}.COMPRESSOR_TRAIN.STAGES[0].{EcalcYamlKeywords.models_type_compressor_train_stage_control_margin_unit}"
        in error_2
    )
    assert "This keyword is missing, it is required" in error_2
