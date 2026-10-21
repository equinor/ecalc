import pytest
from pydantic import ValidationError

from libecalc.presentation.yaml.yaml_types.energy.yaml_generator_definition import YamlGeneratorDefinition


def test_accepts_inline_and_file_curves():
    YamlGeneratorDefinition.model_validate({"CURVE": {"POWER": [0, 10], "FUEL": [0, 50000]}})
    YamlGeneratorDefinition.model_validate({"CURVE": {"FILE": "curve.csv"}})


@pytest.mark.parametrize(
    ("curve", "message"),
    [
        ({"POWER": [0, 10], "FUEL": [0, 5, 10]}, "equal number"),
        ({"POWER": [10, 0], "FUEL": [5, 0]}, "strictly increasing"),
        ({"POWER": [0, 10], "FUEL": [0, -5]}, "must not be negative"),
    ],
    ids=["unequal_lengths", "powers_not_increasing", "negative_fuel"],
)
def test_rejects_invalid_definition(curve, message):
    with pytest.raises(ValidationError, match=message):
        YamlGeneratorDefinition.model_validate({"CURVE": curve})
