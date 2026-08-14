import pytest
from pydantic import Field

from libecalc.presentation.yaml.definition_expander import expand_definitions
from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.process.yaml_process_pipeline import (
    YamlProcessPipeline,
)
from libecalc.presentation.yaml.yaml_types.process.yaml_process_references import DefinitionReference
from libecalc.presentation.yaml.yaml_types.process.yaml_process_units import (
    YamlLiquidRemoverDefinition,
    YamlPressureDropperDefinition,
)


class TestResolveDefinitions:
    def test_resolves_string_reference(self):
        pipeline = YamlProcessPipeline.model_validate(
            {
                "NAME": "p",
                "PROCESS_UNITS": [{"TARGET": "my_dropper"}],
            }
        )
        defs = {
            "my_dropper": YamlPressureDropperDefinition.model_validate(
                {"TYPE": "PRESSURE_DROPPER", "PRESSURE_DROP": "5"}
            )
        }

        resolved = expand_definitions(pipeline, defs)

        assert isinstance(resolved.process_units[0].target, YamlPressureDropperDefinition)
        assert resolved.process_units[0].target.pressure_drop == "5"

    def test_preserves_inline_definition(self):
        pipeline = YamlProcessPipeline.model_validate(
            {
                "NAME": "p",
                "PROCESS_UNITS": [
                    {"TARGET": {"TYPE": "LIQUID_REMOVER"}},
                ],
            }
        )

        resolved = expand_definitions(pipeline, {})

        assert isinstance(resolved.process_units[0].target, YamlLiquidRemoverDefinition)

    def test_missing_reference_raises_key_error(self):
        pipeline = YamlProcessPipeline.model_validate(
            {
                "NAME": "p",
                "PROCESS_UNITS": [{"TARGET": "nonexistent"}],
            }
        )

        with pytest.raises(KeyError, match="nonexistent"):
            expand_definitions(pipeline, {})

    def test_resolves_multiple_references(self):
        pipeline = YamlProcessPipeline.model_validate(
            {
                "NAME": "p",
                "PROCESS_UNITS": [
                    {"TARGET": "dropper"},
                    {"TARGET": "remover"},
                ],
            }
        )
        defs = {
            "dropper": YamlPressureDropperDefinition.model_validate({"TYPE": "PRESSURE_DROPPER", "PRESSURE_DROP": "3"}),
            "remover": YamlLiquidRemoverDefinition.model_validate({"TYPE": "LIQUID_REMOVER"}),
        }

        resolved = expand_definitions(pipeline, defs)

        assert isinstance(resolved.process_units[0].target, YamlPressureDropperDefinition)
        assert isinstance(resolved.process_units[1].target, YamlLiquidRemoverDefinition)

    def test_mixed_inline_and_reference(self):
        pipeline = YamlProcessPipeline.model_validate(
            {
                "NAME": "p",
                "PROCESS_UNITS": [
                    {"TARGET": "dropper"},
                    {"TARGET": {"TYPE": "LIQUID_REMOVER"}},
                ],
            }
        )
        defs = {
            "dropper": YamlPressureDropperDefinition.model_validate({"TYPE": "PRESSURE_DROPPER", "PRESSURE_DROP": "1"}),
        }

        resolved = expand_definitions(pipeline, defs)

        assert isinstance(resolved.process_units[0].target, YamlPressureDropperDefinition)
        assert isinstance(resolved.process_units[1].target, YamlLiquidRemoverDefinition)

    def test_no_references_returns_equal_model(self):
        pipeline = YamlProcessPipeline.model_validate(
            {
                "NAME": "p",
                "PROCESS_UNITS": [
                    {"TARGET": {"TYPE": "LIQUID_REMOVER"}},
                ],
            }
        )

        resolved = expand_definitions(pipeline, {})

        assert resolved == pipeline

    def test_preserves_instance_name(self):
        pipeline = YamlProcessPipeline.model_validate(
            {
                "NAME": "p",
                "PROCESS_UNITS": [{"TARGET": "dropper", "NAME": "stage1"}],
            }
        )
        defs = {
            "dropper": YamlPressureDropperDefinition.model_validate({"TYPE": "PRESSURE_DROPPER", "PRESSURE_DROP": "5"}),
        }

        resolved = expand_definitions(pipeline, defs)

        assert resolved.process_units[0].name == "stage1"

    def test_non_definition_strings_are_not_resolved(self):
        """Fields typed as plain str (not DefinitionReference unions) should be left alone."""
        pipeline = YamlProcessPipeline.model_validate(
            {
                "NAME": "my_pipeline_name",
                "PROCESS_UNITS": [{"TARGET": {"TYPE": "LIQUID_REMOVER"}}],
            }
        )

        resolved = expand_definitions(pipeline, {"my_pipeline_name": "should_not_replace"})

        assert resolved.name == "my_pipeline_name"

    def test_resolves_references_in_dict_values(self):
        """DefinitionReference inside dict values should be resolved."""

        class Inner(YamlBase):
            target: YamlPressureDropperDefinition | DefinitionReference

        class Outer(YamlBase):
            items: dict[str, Inner] = Field(default_factory=dict)

        outer = Outer.model_validate({"ITEMS": {"a": {"TARGET": "dropper"}}})
        defs = {
            "dropper": YamlPressureDropperDefinition.model_validate({"TYPE": "PRESSURE_DROPPER", "PRESSURE_DROP": "2"}),
        }

        resolved = expand_definitions(outer, defs)

        assert isinstance(resolved.items["a"].target, YamlPressureDropperDefinition)
