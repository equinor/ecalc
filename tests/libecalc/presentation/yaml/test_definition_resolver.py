import pytest

from libecalc.presentation.yaml.definition_expander import DefinitionNotFoundError, expand_definitions
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.process.yaml_fluid_definitions import YamlPredefinedFluidDefinition
from libecalc.presentation.yaml.yaml_types.streams.yaml_inlet_stream import YamlInletStream
from libecalc.testing.process_builders import (
    YamlInletStreamBuilder,
    YamlMixerBuilder,
    YamlPredefinedFluidDefinitionBuilder,
    YamlProcessPipelineBuilder,
)

FLUID = YamlPredefinedFluidDefinitionBuilder().with_test_data().validate()
DEFINITIONS = {"medium_gas": FLUID}


def _stream(fluid: str | YamlPredefinedFluidDefinition, name: str = "inlet") -> YamlInletStream:
    return YamlInletStreamBuilder().with_test_data().with_name(name).with_fluid(fluid).validate()


def test_resolves_fluid_reference():
    resolved = expand_definitions(_stream("medium_gas"), DEFINITIONS)

    assert resolved.fluid == FLUID


def test_inline_fluid_gives_equal_model():
    stream = _stream(FLUID)

    assert expand_definitions(stream, DEFINITIONS) == stream


def test_resolves_fluid_reference_in_mixer_sidestream_of_pipeline():
    pipeline = (
        YamlProcessPipelineBuilder()
        .with_name("train")
        .with_item(YamlMixerBuilder().with_sidestream(_stream("medium_gas")).validate())
        .validate()
    )

    resolved = expand_definitions(pipeline, DEFINITIONS)

    assert resolved.process_units[0].sidestream.fluid == FLUID


def test_resolves_fluid_reference_in_dict_values():
    class Streams(YamlBase):
        streams: dict[str, YamlInletStream]

    resolved = expand_definitions(Streams(streams={"inlet": _stream("medium_gas")}), DEFINITIONS)

    assert resolved.streams["inlet"].fluid == FLUID


def test_leaves_plain_string_fields_alone():
    resolved = expand_definitions(_stream(FLUID, name="medium_gas"), DEFINITIONS)

    assert resolved.name == "medium_gas"


def test_unknown_reference_raises():
    with pytest.raises(DefinitionNotFoundError, match="'unknown_gas' not found"):
        expand_definitions(_stream("unknown_gas"), DEFINITIONS)
