import pytest
from pydantic import ValidationError

from libecalc.presentation.yaml.yaml_types.energy.yaml_turbine_definition import YamlTurbineDefinition


def test_accepts_inline_and_file_curves():
    YamlTurbineDefinition.model_validate({"CURVE": {"LOAD": [5, 10], "EFFICIENCY": [0.2, 0.3]}})
    YamlTurbineDefinition.model_validate({"CURVE": {"FILE": "curve.csv"}})


@pytest.mark.parametrize(
    ("curve", "message"),
    [
        ({"LOAD": [0, 10], "EFFICIENCY": [0, 0.2, 0.3]}, "equal number"),
        ({"LOAD": [10, 0], "EFFICIENCY": [0.3, 0.2]}, "strictly increasing"),
        ({"LOAD": [0, 10], "EFFICIENCY": [0, 0.3]}, "above 0 and up to 1"),
        ({"LOAD": [5, 10], "EFFICIENCY": [0.2, 1.2]}, "above 0 and up to 1"),
    ],
    ids=["unequal_lengths", "loads_not_increasing", "zero_efficiency", "efficiency_above_one"],
)
def test_rejects_invalid_definition(curve, message):
    with pytest.raises(ValidationError, match=message):
        YamlTurbineDefinition.model_validate({"CURVE": curve})
