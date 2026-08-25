"""Tests for get_expected_types — the function that extracts concrete types
from union annotations containing DefinitionReference."""

from typing import Annotated, Union

import pytest
from pydantic import Field

from libecalc.presentation.yaml.definition_expander import get_expected_types
from libecalc.presentation.yaml.yaml_types.process.yaml_process_references import DefinitionReference
from libecalc.presentation.yaml.yaml_types.process.yaml_process_units import (
    YamlCompressorDefinition,
    YamlLiquidRemoverDefinition,
    YamlMixerDefinition,
    YamlPressureDropperDefinition,
    YamlProcessUnitDefinition,
    YamlSplitterDefinition,
    YamlTemperatureSetterDefinition,
)


# --- Dummy types for testing ---
class Alpha:
    pass


class Beta:
    pass


class Gamma:
    pass


@pytest.mark.parametrize(
    "annotation, expected",
    [
        pytest.param(
            Alpha | DefinitionReference,
            [Alpha],
            id="simple_union_single_type",
        ),
        pytest.param(
            Alpha | Beta | DefinitionReference,
            [Alpha, Beta],
            id="simple_union_multiple_types",
        ),
        pytest.param(
            Union[Alpha, DefinitionReference],
            [Alpha],
            id="typing_union_single_type",
        ),
        pytest.param(
            Union[Alpha, Beta, Gamma, DefinitionReference],
            [Alpha, Beta, Gamma],
            id="typing_union_many_types",
        ),
        pytest.param(
            Annotated[Alpha | Beta, Field(discriminator="type")] | DefinitionReference,
            [Alpha, Beta],
            id="annotated_discriminated_union",
        ),
        pytest.param(
            Annotated[Union[Alpha, Beta, Gamma], Field(discriminator="type")] | DefinitionReference,
            [Alpha, Beta, Gamma],
            id="annotated_typing_union",
        ),
        pytest.param(
            Alpha | Beta,
            [Alpha, Beta],
            id="union_without_definition_reference",
        ),
        pytest.param(
            int | DefinitionReference,
            [int],
            id="builtin_type_in_union",
        ),
    ],
)
def test_get_expected_types(annotation, expected):
    result = get_expected_types(annotation)
    assert result == expected


def test_get_expected_types_with_real_process_unit_annotation():
    """Verify against the actual YamlProcessUnitDefinition annotation used in the codebase."""
    # This is the annotation used on YamlProcessUnitInstance.target:
    #   YamlProcessUnitDefinition | DefinitionReference
    # where YamlProcessUnitDefinition is Annotated[Union[Compressor, PressureDropper, ...], Field(discriminator="type")]
    annotation = YamlProcessUnitDefinition | DefinitionReference

    result = get_expected_types(annotation)
    assert set(result) == {
        YamlCompressorDefinition,
        YamlPressureDropperDefinition,
        YamlTemperatureSetterDefinition,
        YamlLiquidRemoverDefinition,
        YamlMixerDefinition,
        YamlSplitterDefinition,
    }


def test_get_expected_types_with_real_compressor_event_annotation():
    """Verify against the change_from/change_to annotation: YamlCompressorDefinition | DefinitionReference."""
    annotation = YamlCompressorDefinition | DefinitionReference

    result = get_expected_types(annotation)
    assert result == [YamlCompressorDefinition]
