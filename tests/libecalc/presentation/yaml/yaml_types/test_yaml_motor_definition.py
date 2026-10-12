import pytest
from pydantic import ValidationError

from libecalc.presentation.yaml.yaml_types.energy.yaml_motor_definition import YamlMotorDefinition


def test_accepts_inline_and_file_curves():
    YamlMotorDefinition.model_validate({"CURVE": {"LOAD": [1, 10], "EFFICIENCY": [0.9, 0.95]}})
    YamlMotorDefinition.model_validate({"CURVE": {"FILE": "curve.csv"}})


def test_rejects_invalid_inline_curve():
    with pytest.raises(ValidationError, match="above 0 and up to 1"):
        YamlMotorDefinition.model_validate({"CURVE": {"LOAD": [1, 10], "EFFICIENCY": [0.9, 1.2]}})
