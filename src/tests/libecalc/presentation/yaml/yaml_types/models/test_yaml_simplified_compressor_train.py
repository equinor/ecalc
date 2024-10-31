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

    # Control margin is not allowed:
    assert (
        f"{EcalcYamlKeywords.models_type_compressor_train_simplified}"
        f".COMPRESSOR_TRAIN.YamlCompressorStages[YamlCompressorStage].STAGES[0]."
        f"{EcalcYamlKeywords.models_type_compressor_train_stage_control_margin}\n"
        f"\tMessage: This is not a valid keyword" in str(exc_info.value)
    )

    # Control margin unit is not allowed:
    assert (
        f"{EcalcYamlKeywords.models_type_compressor_train_simplified}."
        f"COMPRESSOR_TRAIN.YamlCompressorStages[YamlCompressorStage].STAGES[0]."
        f"{EcalcYamlKeywords.models_type_compressor_train_stage_control_margin_unit}\n"
        f"\tMessage: This is not a valid keyword" in str(exc_info.value)
    )

    # Pressure drop ahead of stage is not allowed:
    assert (
        f"{EcalcYamlKeywords.models_type_compressor_train_simplified}."
        f"COMPRESSOR_TRAIN.YamlCompressorStages[YamlCompressorStage].STAGES[0]."
        f"{EcalcYamlKeywords.models_type_compressor_train_pressure_drop_ahead_of_stage}\n"
        f"\tMessage: This is not a valid keyword" in str(exc_info.value)
    )


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

    # Single speed compressor chart is not allowed for simplified trains:
    assert (
        f"{EcalcYamlKeywords.consumer_chart_type_single_speed} compressor chart is not supported for "
        f"{EcalcYamlKeywords.models_type_compressor_train_simplified}." in str(exc_info.value)
    )
