"""
Tests verifying that process system definitions and instances produce clear error messages
when references point to non-existent definitions or definitions of an incorrect type.

These tests are expected to FAIL currently — proper validation will be added later.
"""

from io import StringIO

import pytest
from inline_snapshot import snapshot

from libecalc.presentation.yaml.model_validation_exception import ModelValidationException
from libecalc.presentation.yaml.yaml_entities import ResourceStream
from libecalc.presentation.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel
from libecalc.presentation.yaml.yaml_types.process.yaml_process_pipeline import (
    PipelineEventAction,
    PipelineEventChangeType,
    YamlPipelineEvent,
)
from libecalc.testing.process_builders import (
    YamlCommonStreamDistributionBuilder,
    YamlCompressorModelChartBuilder,
    YamlDefinitionsBuilder,
    YamlPredefinedFluidDefinitionBuilder,
    YamlProcessPipelineBuilder,
    YamlProcessSimulationBuilder,
    compressors_in,
    shaft_for,
)
from libecalc.testing.yaml_builder import YamlAssetBuilder


def _asset_to_stream(asset) -> ResourceStream:
    """Serialize a YamlAsset to a ResourceStream for use with yaml_model_factory."""
    asset_dict = asset.model_dump(serialize_as_any=True, mode="json", exclude_unset=True, by_alias=True)
    yaml_string = PyYamlYamlModel.dump_yaml(yaml_dict=asset_dict)
    return ResourceStream(name="test_model", stream=StringIO(yaml_string))


class TestDefinitionReferenceNotFound:
    """Tests for when a DefinitionReference points to a name that does not exist in definitions."""

    @pytest.mark.parametrize(
        "model, change_to",
        [
            pytest.param("ghost", "compressor_model", id="MODEL"),
            pytest.param("compressor_model", "ghost", id="CHANGE_TO"),
        ],
    )
    def test_compressor_model_reference_not_found_is_reported(self, yaml_model_factory, model, change_to):
        pipeline = (
            YamlProcessPipelineBuilder()
            .with_name("train_1")
            .with_compressor_item(compressor="compressor_1", model=model)
            .with_events(
                [
                    YamlPipelineEvent(
                        type=PipelineEventAction.CHANGE,
                        change_target="compressor_1",
                        change_to=change_to,
                        change_type=PipelineEventChangeType.REBUNDLE,
                        ref="rebundle",
                    )
                ]
            )
            .validate()
        )
        simulation = (
            YamlProcessSimulationBuilder()
            .with_name("my_sim")
            .with_pipeline(pipeline)
            .with_stream_distribution(YamlCommonStreamDistributionBuilder().with_test_data().validate())
            .validate()
        )
        asset = (
            YamlAssetBuilder()
            .with_test_data()
            .with_shafts([shaft_for(pipeline)])
            .with_compressors(compressors_in(pipeline))
            .with_process_pipelines({"train_1": pipeline})
            .with_process_simulations([simulation])
            .with_definitions(
                YamlDefinitionsBuilder()
                .with_compressor_model(
                    "compressor_model", YamlCompressorModelChartBuilder().with_test_data().validate()
                )
                .validate()
            )
            .validate()
        )
        model = yaml_model_factory(configuration=_asset_to_stream(asset), resources={})

        with pytest.raises(ModelValidationException, match="'ghost' not found. Available definitions"):
            model.get_process_simulations()


class TestDefinitionReferenceWrongType:
    """Tests for when a DefinitionReference resolves to a definition of an incompatible type."""

    @pytest.mark.snapshot
    @pytest.mark.inlinesnapshot
    def test_pipeline_unit_references_fluid_definition(self, yaml_model_factory):
        """A process unit instance referencing a fluid definition should produce a type error."""

        pipeline = (
            YamlProcessPipelineBuilder().with_name("train_1").with_item(target="my_fluid", name="stage_1").validate()
        )

        sim_builder = (
            YamlProcessSimulationBuilder()
            .with_name("my_sim")
            .with_pipeline(pipeline)
            .with_stream_distribution(YamlCommonStreamDistributionBuilder().with_test_data().validate())
        )
        simulation = sim_builder.validate()

        fluid_def = YamlPredefinedFluidDefinitionBuilder().with_test_data().validate()
        definitions = YamlDefinitionsBuilder().with_fluid("my_fluid", fluid_def).validate()

        asset = (
            YamlAssetBuilder()
            .with_test_data()
            .with_shafts([shaft_for(pipeline)])
            .with_compressors(compressors_in(pipeline))
            .with_process_pipelines({"train_1": pipeline})
            .with_process_simulations([simulation])
            .with_definitions(definitions)
        ).validate()

        model = yaml_model_factory(configuration=_asset_to_stream(asset), resources={})

        with pytest.raises(ModelValidationException) as exc_info:
            model.get_process_simulations()

        assert str(exc_info.value) == snapshot("""\
Validation error

	Object starting on line 23
	Location: PROCESS_PIPELINES.train_1
	Message: Definition reference 'my_fluid' resolved to type 'YamlPredefinedFluidDefinition', but expected one of: YamlPressureDropperDefinition, YamlTemperatureSetterDefinition, YamlLiquidRemoverDefinition, YamlMixerDefinition, YamlSplitterDefinition
""")
