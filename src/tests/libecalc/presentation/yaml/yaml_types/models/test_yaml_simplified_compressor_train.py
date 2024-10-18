from io import StringIO
from pathlib import Path

import pytest

from conftest import (
    OverridableStreamConfigurationService,
    yaml_simplified_train_with_control_margin_and_pressure_drop,
    yaml_simplified_train_wrong_chart,
)
from ecalc_cli.infrastructure.file_resource_service import FileResourceService
from libecalc.common.time_utils import Frequency
from libecalc.presentation.yaml.model import YamlModel
from libecalc.presentation.yaml.validation_errors import ValidationError
from libecalc.presentation.yaml.yaml_entities import ResourceStream
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords


def test_control_margin_and_pressure_drop_not_allowed():
    configuration_service = OverridableStreamConfigurationService(
        stream=ResourceStream(name="", stream=StringIO(yaml_simplified_train_with_control_margin_and_pressure_drop))
    )
    resource_service = FileResourceService(working_directory=Path(""))

    model = YamlModel(
        configuration_service=configuration_service,
        resource_service=resource_service,
        output_frequency=Frequency.YEAR,
    )

    with pytest.raises(ValidationError) as exc_info:
        model.validate_for_run()

    errors = exc_info.value.errors()

    # Control margin is not allowed:
    assert (
        f"MODELS[2].{EcalcYamlKeywords.models_type_compressor_train_simplified}.COMPRESSOR_TRAIN.YamlCompressorStages[YamlCompressorStage].STAGES[0].{EcalcYamlKeywords.models_type_compressor_train_stage_control_margin}"
        in str(errors[0])
    )
    assert "This is not a valid keyword" in str(errors[0])

    # Control margin unit is not allowed:
    assert (
        f"MODELS[2].{EcalcYamlKeywords.models_type_compressor_train_simplified}.COMPRESSOR_TRAIN.YamlCompressorStages[YamlCompressorStage].STAGES[0].{EcalcYamlKeywords.models_type_compressor_train_stage_control_margin_unit}"
        in str(errors[1])
    )
    assert "This is not a valid keyword" in str(errors[1])

    # Pressure drop ahead of stage is not allowed:
    assert (
        f"MODELS[2].{EcalcYamlKeywords.models_type_compressor_train_simplified}.COMPRESSOR_TRAIN.YamlCompressorStages[YamlCompressorStage].STAGES[0].{EcalcYamlKeywords.models_type_compressor_train_pressure_drop_ahead_of_stage}"
        in str(errors[2])
    )
    assert "This is not a valid keyword" in str(errors[2])


def test_single_speed_chart_not_allowed():
    configuration_service = OverridableStreamConfigurationService(
        stream=ResourceStream(name="", stream=StringIO(yaml_simplified_train_wrong_chart))
    )
    resource_service = FileResourceService(working_directory=Path(""))

    model = YamlModel(
        configuration_service=configuration_service,
        resource_service=resource_service,
        output_frequency=Frequency.YEAR,
    )

    with pytest.raises(ValidationError) as exc_info:
        model.validate_for_run()

    errors = exc_info.value.errors()

    # Single speed compressor chart is not allowed for simplified trains:
    assert (
        f"{EcalcYamlKeywords.consumer_chart_type_single_speed} compressor chart is not supported for {EcalcYamlKeywords.models_type_compressor_train_simplified}."
        in str(errors[0])
    )
