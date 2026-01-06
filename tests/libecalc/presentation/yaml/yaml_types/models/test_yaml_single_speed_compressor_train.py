from io import StringIO
from pathlib import Path

import pytest

from ecalc_cli.infrastructure.file_resource_service import FileResourceService
from libecalc.presentation.yaml.model import YamlModel
from libecalc.presentation.yaml.model_validation_exception import ModelValidationException
from libecalc.presentation.yaml.yaml_entities import ResourceStream
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords


def test_control_margin_required(configuration_service_factory, yaml_single_speed_train_without_control_margin):
    configuration_service = configuration_service_factory(
        ResourceStream(name="", stream=StringIO(yaml_single_speed_train_without_control_margin))
    )
    configuration = configuration_service.get_configuration()
    resource_service = FileResourceService(working_directory=Path(""), configuration=configuration)

    model = YamlModel(
        configuration=configuration,
        resource_service=resource_service,
    )

    with pytest.raises(ModelValidationException) as exc_info:
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
