"""
Tests verifying that process system definitions and instances produce clear error messages
when references point to non-existent definitions or definitions of an incorrect type.

These tests are expected to FAIL currently — proper validation will be added later.
"""

from io import StringIO

import pytest
from inline_snapshot import snapshot

from libecalc.ecalc_model.ecalc_event import EcalcEventService
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
    YamlCompressorBuilder,
    YamlDefinitionsBuilder,
    YamlPredefinedFluidDefinitionBuilder,
    YamlPressureDropperBuilder,
    YamlProcessPipelineBuilder,
    YamlProcessSimulationBuilder,
)
from libecalc.testing.yaml_builder import YamlAssetBuilder


def _asset_to_stream(asset) -> ResourceStream:
    """Serialize a YamlAsset to a ResourceStream for use with yaml_model_factory."""
    asset_dict = asset.model_dump(serialize_as_any=True, mode="json", exclude_unset=True, by_alias=True)
    yaml_string = PyYamlYamlModel.dump_yaml(yaml_dict=asset_dict)
    return ResourceStream(name="test_model", stream=StringIO(yaml_string))


class TestDefinitionReferenceNotFound:
    """Tests for when a DefinitionReference points to a name that does not exist in definitions."""

    @pytest.mark.snapshot
    @pytest.mark.inlinesnapshot
    def test_pipeline_references_nonexistent_definition(self, yaml_model_factory):
        """A pipeline with a process unit referencing a definition that doesn't exist
        should produce a clear error when get_process_simulations is called."""
        pipeline = (
            YamlProcessPipelineBuilder()
            .with_name("train_1")
            .with_item(target="nonexistent_compressor", name="stage_1")
            .validate()
        )

        sim_builder = (
            YamlProcessSimulationBuilder()
            .with_name("my_sim")
            .with_pipeline(pipeline)
            .with_stream_distribution(YamlCommonStreamDistributionBuilder().with_test_data().validate())
        )
        simulation = sim_builder.validate()

        definitions = YamlDefinitionsBuilder().with_test_data().validate()

        asset = (
            YamlAssetBuilder()
            .with_test_data()
            .with_process_pipelines({"train_1": pipeline})
            .with_process_simulations([simulation])
            .with_definitions(definitions)
        ).validate()

        model = yaml_model_factory(configuration=_asset_to_stream(asset), resources={})

        with pytest.raises(ModelValidationException) as exc_info:
            model.get_process_simulations(ecalc_event_service=EcalcEventService(ecalc_events=[]))

        assert str(exc_info.value) == snapshot("""\
Validation error

	Object starting on line 13
	Location: PROCESS_PIPELINES.train_1
	Message: Definition reference 'nonexistent_compressor' not found. Available definitions: []
""")

    @pytest.mark.snapshot
    @pytest.mark.inlinesnapshot
    def test_pipeline_references_misspelled_definition(self, yaml_model_factory):
        """A misspelled definition reference should produce an error listing available definitions."""
        compressor_def = YamlCompressorBuilder().with_test_data().validate()

        pipeline = (
            YamlProcessPipelineBuilder()
            .with_name("train_1")
            .with_item(target="compressor_stge_1", name="stage_1")  # misspelled
            .validate()
        )

        sim_builder = (
            YamlProcessSimulationBuilder()
            .with_name("my_sim")
            .with_pipeline(pipeline)
            .with_stream_distribution(YamlCommonStreamDistributionBuilder().with_test_data().validate())
        )
        simulation = sim_builder.validate()

        definitions = YamlDefinitionsBuilder().with_process_unit("compressor_stage_1", compressor_def).validate()

        asset = (
            YamlAssetBuilder()
            .with_test_data()
            .with_process_pipelines({"train_1": pipeline})
            .with_process_simulations([simulation])
            .with_definitions(definitions)
        ).validate()

        model = yaml_model_factory(configuration=_asset_to_stream(asset), resources={})

        with pytest.raises(ModelValidationException) as exc_info:
            model.get_process_simulations(ecalc_event_service=EcalcEventService(ecalc_events=[]))

        assert str(exc_info.value) == snapshot("""\
Validation error

	Object starting on line 42
	Location: PROCESS_PIPELINES.train_1
	Message: Definition reference 'compressor_stge_1' not found. Available definitions: ['compressor_stage_1']
""")


class TestDefinitionReferenceWrongType:
    """Tests for when a DefinitionReference resolves to a definition of an incompatible type."""

    @pytest.mark.snapshot
    @pytest.mark.inlinesnapshot
    def test_pipeline_unit_references_fluid_definition(self, yaml_model_factory):
        """A process unit instance referencing a fluid definition should produce a type error."""
        fluid_def = YamlPredefinedFluidDefinitionBuilder().with_test_data().validate()

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

        definitions = YamlDefinitionsBuilder().with_fluid("my_fluid", fluid_def).validate()

        asset = (
            YamlAssetBuilder()
            .with_test_data()
            .with_process_pipelines({"train_1": pipeline})
            .with_process_simulations([simulation])
            .with_definitions(definitions)
        ).validate()

        model = yaml_model_factory(configuration=_asset_to_stream(asset), resources={})

        with pytest.raises(ModelValidationException) as exc_info:
            model.get_process_simulations(ecalc_event_service=EcalcEventService(ecalc_events=[]))

        assert str(exc_info.value) == snapshot("""\
Validation error

	Object starting on line 17
	Location: PROCESS_PIPELINES.train_1
	Message: Definition reference 'my_fluid' resolved to type 'YamlPredefinedFluidDefinition', but expected one of: YamlCompressorDefinition, YamlPressureDropperDefinition, YamlTemperatureSetterDefinition, YamlLiquidRemoverDefinition, YamlMixerDefinition, YamlSplitterDefinition
""")

    @pytest.mark.snapshot
    @pytest.mark.inlinesnapshot
    def test_pipeline_unit_references_wrong_process_unit_type_in_event(self, yaml_model_factory):
        """A pipeline event's change_from/change_to expecting a COMPRESSOR but given a PRESSURE_DROPPER
        should produce a clear type error."""
        pressure_dropper_def = YamlPressureDropperBuilder().with_test_data().validate()
        compressor_def = YamlCompressorBuilder().with_test_data().validate()

        event = YamlPipelineEvent(
            type=PipelineEventAction.CHANGE,
            change_target="stage_1",
            change_from="my_pressure_dropper",
            change_to="my_pressure_dropper",
            change_type=PipelineEventChangeType.REBUNDLE,
            ref="some_event",
        )

        pipeline = (
            YamlProcessPipelineBuilder()
            .with_name("train_1")
            .with_item(target=compressor_def, name="stage_1")
            .with_events([event])
            .validate()
        )

        sim_builder = (
            YamlProcessSimulationBuilder()
            .with_name("my_sim")
            .with_pipeline(pipeline)
            .with_stream_distribution(YamlCommonStreamDistributionBuilder().with_test_data().validate())
        )
        simulation = sim_builder.validate()

        definitions = YamlDefinitionsBuilder().with_process_unit("my_pressure_dropper", pressure_dropper_def).validate()

        asset = (
            YamlAssetBuilder()
            .with_test_data()
            .with_process_pipelines({"train_1": pipeline})
            .with_process_simulations([simulation])
            .with_definitions(definitions)
        ).validate()

        model = yaml_model_factory(configuration=_asset_to_stream(asset), resources={})

        with pytest.raises(ModelValidationException) as exc_info:
            model.get_process_simulations(ecalc_event_service=EcalcEventService(ecalc_events=[]))

        assert str(exc_info.value) == snapshot("""\
Validation error

	Object starting on line 16
	Location: PROCESS_PIPELINES.train_1
	Message: Definition reference 'my_pressure_dropper' resolved to type 'YamlPressureDropperDefinition', but expected one of: YamlCompressorDefinition
""")
