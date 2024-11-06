from io import StringIO
from pathlib import Path

import pytest

from conftest import (
    yaml_single_speed_train_without_control_margin,
)
from ecalc_cli.infrastructure.file_resource_service import FileResourceService
from libecalc.common.time_utils import Frequency
from libecalc.presentation.yaml.model import YamlModel
from libecalc.presentation.yaml.validation_errors import ValidationError
from libecalc.presentation.yaml.yaml_entities import ResourceStream
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords


def test_control_margin_required(configuration_service_factory):
    configuration_service = configuration_service_factory(
        ResourceStream(name="", stream=StringIO(yaml_single_speed_train_without_control_margin))
    )
    resource_service = FileResourceService(working_directory=Path(""))

    model = YamlModel(
        configuration_service=configuration_service,
        resource_service=resource_service,
        output_frequency=Frequency.YEAR,
    )

    with pytest.raises(ValidationError) as exc_info:
        model.validate_for_run()

    # Control margin is required for single speed compressor train:
    assert (
        f"{EcalcYamlKeywords.models_type_compressor_train_single_speed}.COMPRESSOR_TRAIN.STAGES[0]."
        f"{EcalcYamlKeywords.models_type_compressor_train_stage_control_margin}\n"
        f"\tMessage: This keyword is missing, it is required" in str(exc_info.value)
    )

    # Control margin unit is required for single speed compressor train:
    assert (
        f"{EcalcYamlKeywords.models_type_compressor_train_single_speed}.COMPRESSOR_TRAIN.STAGES[0]."
        f"{EcalcYamlKeywords.models_type_compressor_train_stage_control_margin_unit}\n"
        f"\tMessage: This keyword is missing, it is required" in str(exc_info.value)
    )
