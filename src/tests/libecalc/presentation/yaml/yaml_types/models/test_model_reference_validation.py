from dataclasses import dataclass

import pytest
from libecalc.presentation.yaml.yaml_types.models.model_reference_validation import (
    InvalidModelReferenceError,
    ModelReferenceNotFound,
    check_model_reference,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_enums import YamlModelType
from libecalc.presentation.yaml.yaml_validation_context import Model


@dataclass
class Model(Model):
    name: str
    type: str


class TestCheckModelReference:
    def test_not_found(self):
        with pytest.raises(ModelReferenceNotFound):
            check_model_reference("some_model", available_models={}, allowed_types=[])

    def test_invalid_type(self):
        allowed_type = "ALLOWED"
        model_name = "valid_model"
        with pytest.raises(InvalidModelReferenceError):
            check_model_reference(
                model_name,
                available_models={model_name: Model(name=model_name, type="SOME_OTHER_TYPE")},
                allowed_types=[allowed_type],
            )

    def test_found_and_correct(self):
        allowed_type = YamlModelType.FLUID
        model_name = "valid_model"
        assert check_model_reference(
            model_name,
            available_models={model_name: Model(name=model_name, type=allowed_type)},
            allowed_types=[allowed_type],
        )
