import pytest
from pydantic import BaseModel, ValidationError

from libecalc.presentation.yaml.yaml_types.energy.yaml_generator_definition import YamlGeneratorDefinition
from libecalc.presentation.yaml.yaml_types.energy.yaml_generator_set_definition import (
    YamlGeneratorSetEngineDefinition,
    YamlGeneratorSetModel,
)


class _Wrapper(BaseModel):
    model: YamlGeneratorSetModel


def test_discriminates_gas_turbine():
    wrapper = _Wrapper.model_validate(
        {"model": {"TYPE": "GAS_TURBINE_DRIVEN", "ENGINE": "some_curve_ref", "GENERATOR_EFFICIENCY": 0.97}}
    )

    assert isinstance(wrapper.model, YamlGeneratorSetEngineDefinition)
    assert wrapper.model.type == "GAS_TURBINE_DRIVEN"


def test_discriminates_diesel_engine():
    wrapper = _Wrapper.model_validate(
        {"model": {"TYPE": "DIESEL_ENGINE_DRIVEN", "ENGINE": "some_curve_ref", "GENERATOR_EFFICIENCY": 0.9}}
    )

    assert isinstance(wrapper.model, YamlGeneratorSetEngineDefinition)
    assert wrapper.model.type == "DIESEL_ENGINE_DRIVEN"


def test_discriminates_curve_reference():
    wrapper = _Wrapper.model_validate({"model": "some_curve_ref"})

    assert wrapper.model == "some_curve_ref"


def test_discriminates_inline_curve():
    wrapper = _Wrapper.model_validate(
        {"model": {"TYPE": "POWER_TO_FUEL", "CURVE": {"POWER": [0, 5, 10], "FUEL": [0, 20000, 38000]}}}
    )

    assert isinstance(wrapper.model, YamlGeneratorDefinition)


def test_typo_in_engine_type_gives_clear_error_instead_of_matching_curve():
    with pytest.raises(ValidationError) as exc_info:
        _Wrapper.model_validate(
            {"model": {"TYPE": "GAS_TURBIN", "ENGINE": "some_curve_ref", "GENERATOR_EFFICIENCY": 0.97}}
        )

    message = str(exc_info.value)
    assert "Unrecognized TYPE for generator set MODEL: 'GAS_TURBIN'" in message


def test_empty_dict_gives_clear_error():
    with pytest.raises(ValidationError) as exc_info:
        _Wrapper.model_validate({"model": {}})

    message = str(exc_info.value)
    assert "model.curve.TYPE" in message
    assert "model.curve.CURVE" in message


def test_engine_type_with_missing_engine_field_reports_engine_errors_not_curve_errors():
    """TYPE alone must route to the engine shape, so a missing ENGINE is reported clearly instead of a
    confusing "TYPE should be POWER_TO_FUEL"/"CURVE required" error from the unrelated curve shape."""
    with pytest.raises(ValidationError) as exc_info:
        _Wrapper.model_validate({"model": {"TYPE": "GAS_TURBINE_DRIVEN"}})

    message = str(exc_info.value)
    assert "model.engine.ENGINE" in message
    assert "model.engine.GENERATOR_EFFICIENCY" in message
    assert "curve" not in message.lower()


def test_curve_with_stray_engine_field_is_rejected_as_extra():
    with pytest.raises(ValidationError) as exc_info:
        _Wrapper.model_validate(
            {
                "model": {
                    "TYPE": "POWER_TO_FUEL",
                    "CURVE": {"POWER": [0, 5, 10], "FUEL": [0, 20000, 38000]},
                    "GENERATOR_EFFICIENCY": 0.9,
                }
            }
        )

    message = str(exc_info.value)
    assert "model.curve.GENERATOR_EFFICIENCY" in message
    assert "Extra inputs are not permitted" in message
