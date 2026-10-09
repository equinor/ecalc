import pytest
from pydantic import ValidationError

from libecalc.presentation.yaml.yaml_types.energy.yaml_turbine_definition import YamlTurbineDefinition


def test_accepts_inline_and_file_curves():
    YamlTurbineDefinition.model_validate(
        {"LOWER_HEATING_VALUE": 38, "CURVE": {"LOAD": [5, 10], "EFFICIENCY": [0.2, 0.3]}}
    )
    YamlTurbineDefinition.model_validate({"LOWER_HEATING_VALUE": 38, "CURVE": {"FILE": "curve.csv"}})


@pytest.mark.parametrize(
    ("lhv", "curve", "message"),
    [
        (38, {"LOAD": [0, 10], "EFFICIENCY": [0, 0.2, 0.3]}, "equal number"),
        (38, {"LOAD": [10, 0], "EFFICIENCY": [0.3, 0.2]}, "strictly increasing"),
        (38, {"LOAD": [0, 10], "EFFICIENCY": [0, 0.3]}, "above 0 and up to 1"),
        (38, {"LOAD": [5, 10], "EFFICIENCY": [0.2, 1.2]}, "above 0 and up to 1"),
        (0, {"LOAD": [5, 10], "EFFICIENCY": [0.2, 0.3]}, "greater than 0"),
    ],
    ids=["unequal_lengths", "loads_not_increasing", "zero_efficiency", "efficiency_above_one", "zero_heating_value"],
)
def test_rejects_invalid_definition(lhv, curve, message):
    with pytest.raises(ValidationError, match=message):
        YamlTurbineDefinition.model_validate({"LOWER_HEATING_VALUE": lhv, "CURVE": curve})


@pytest.mark.parametrize("lhv", [float("inf"), float("nan")])
def test_rejects_non_finite_heating_value_with_file_curve(lhv):
    with pytest.raises(ValidationError, match="finite"):
        YamlTurbineDefinition.model_validate({"LOWER_HEATING_VALUE": lhv, "CURVE": {"FILE": "curve.csv"}})
