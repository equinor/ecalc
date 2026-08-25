"""
Tests verifying that process system instance references produce clear error messages
when they refer to pipelines, process units, or other objects that do not exist.

Instance references (InstanceReference) are string names that point to named objects
like pipelines, process units within pipelines, or inlet streams. Unlike definition
references (DefinitionReference), these are resolved by the reference service rather
than the definition expander.
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
from libecalc.presentation.yaml.yaml_types.process.yaml_process_simulation import YamlProcessConstraint
from libecalc.presentation.yaml.yaml_types.process.yaml_stream_distribution import (
    YamlOverflow,
)
from libecalc.process.process_solver.anti_surge.anti_surge_strategy import AntiSurgeType
from libecalc.testing.process_builders import (
    YamlCommonStreamDistributionBuilder,
    YamlCompressorBuilder,
    YamlDefinitionsBuilder,
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


def _build_pipeline(name="train_1"):
    return (
        YamlProcessPipelineBuilder()
        .with_name(name)
        .with_item(target=YamlPressureDropperBuilder().with_test_data().validate(), name="dropper")
        .with_item(target=YamlCompressorBuilder().with_test_data().validate(), name="compressor")
        .validate()
    )


class TestTargetReferencesNonexistentPipeline:
    """Tests for when a process simulation's targets list references a pipeline that doesn't exist."""

    @pytest.mark.snapshot
    @pytest.mark.inlinesnapshot
    def test_target_references_nonexistent_pipeline(self, yaml_model_factory):
        """A process simulation targeting a pipeline name that is not in PROCESS_PIPELINES
        should produce a clear ModelValidationException."""
        pipeline = _build_pipeline("train_1")

        simulation = (
            YamlProcessSimulationBuilder()
            .with_name("my_sim")
            .with_target("nonexistent_pipeline")
            .with_pipeline(pipeline)
            .with_stream_distribution(YamlCommonStreamDistributionBuilder().with_test_data().validate())
        ).validate()

        asset = (
            YamlAssetBuilder()
            .with_test_data()
            .with_process_pipelines({"train_1": pipeline})
            .with_process_simulations([simulation])
            .with_definitions(YamlDefinitionsBuilder().with_test_data().validate())
        ).validate()

        model = yaml_model_factory(configuration=_asset_to_stream(asset), resources={})

        with pytest.raises(ModelValidationException) as exc_info:
            model.get_process_simulations(ecalc_event_service=EcalcEventService(ecalc_events=[]))

        assert str(exc_info.value) == snapshot("""\
Validation error

	Object starting on line 52
	Location: PROCESS_SIMULATIONS.my_sim
	Message: Invalid process reference 'nonexistent_pipeline'. Available references: fuel, train_1, my_sim
""")


class TestConstraintReferencesInvalid:
    """Tests for when constraint keys don't match target pipelines."""

    @pytest.mark.snapshot
    @pytest.mark.inlinesnapshot
    def test_constraint_for_nonexistent_pipeline(self, yaml_model_factory):
        """A constraint key referencing a pipeline not in targets should produce a clear error."""
        pipeline = _build_pipeline("train_1")

        constraint = YamlProcessConstraint(
            process_unit="compressor",
            outlet_pressure=100.0,
            pressure_control="DOWNSTREAM_CHOKE",
            anti_surge=AntiSurgeType.INDIVIDUAL_ASV,
        )

        simulation = (
            YamlProcessSimulationBuilder()
            .with_name("my_sim")
            .with_pipeline(pipeline)
            .with_constraint("nonexistent_pipeline", [constraint])
            .with_stream_distribution(YamlCommonStreamDistributionBuilder().with_test_data().validate())
        ).validate()

        asset = (
            YamlAssetBuilder()
            .with_test_data()
            .with_process_pipelines({"train_1": pipeline})
            .with_process_simulations([simulation])
            .with_definitions(YamlDefinitionsBuilder().with_test_data().validate())
        ).validate()

        model = yaml_model_factory(configuration=_asset_to_stream(asset), resources={})

        with pytest.raises(ModelValidationException) as exc_info:
            model.get_process_simulations(ecalc_event_service=EcalcEventService(ecalc_events=[]))

        assert str(exc_info.value) == snapshot("""\
Validation error

	Object starting on line 52
	Location: PROCESS_SIMULATIONS.my_sim
	Message: Invalid process reference 'nonexistent_pipeline'. Available references: fuel, train_1, my_sim
""")

    @pytest.mark.snapshot
    @pytest.mark.inlinesnapshot
    def test_target_pipeline_missing_constraint(self, yaml_model_factory):
        """A target pipeline with no matching constraint entry should produce a clear error."""
        pipeline_1 = _build_pipeline("train_1")
        pipeline_2 = _build_pipeline("train_2")

        simulation = (
            YamlProcessSimulationBuilder()
            .with_name("my_sim")
            .with_pipeline(pipeline_1)
            .with_target("train_2")  # add target but no constraint for train_2
            .with_stream_distribution(YamlCommonStreamDistributionBuilder().with_test_data().validate())
        ).validate()

        asset = (
            YamlAssetBuilder()
            .with_test_data()
            .with_process_pipelines({"train_1": pipeline_1, "train_2": pipeline_2})
            .with_process_simulations([simulation])
            .with_definitions(YamlDefinitionsBuilder().with_test_data().validate())
        ).validate()

        model = yaml_model_factory(configuration=_asset_to_stream(asset), resources={})

        with pytest.raises(ModelValidationException) as exc_info:
            model.get_process_simulations(ecalc_event_service=EcalcEventService(ecalc_events=[]))

        assert str(exc_info.value) == snapshot("""\
Validation error

	Object starting on line 90
	Location: PROCESS_SIMULATIONS.my_sim
	Message: Missing constraint for process system 'train_2'
""")


class TestInletStreamReferenceNotFound:
    """Tests for when an inlet stream reference doesn't exist."""

    @pytest.mark.snapshot
    @pytest.mark.inlinesnapshot
    def test_common_stream_references_nonexistent_inlet_stream(self, yaml_model_factory):
        """A common stream distribution referencing an inlet stream that doesn't exist
        should produce a clear error."""
        pipeline = _build_pipeline("train_1")

        stream_distribution = (
            YamlCommonStreamDistributionBuilder().with_inlet_stream("nonexistent_stream").with_rate_fractions([1.0])
        ).validate()

        simulation = (
            YamlProcessSimulationBuilder()
            .with_name("my_sim")
            .with_pipeline(pipeline)
            .with_stream_distribution(stream_distribution)
        ).validate()

        asset = (
            YamlAssetBuilder()
            .with_test_data()
            .with_process_pipelines({"train_1": pipeline})
            .with_process_simulations([simulation])
            .with_definitions(YamlDefinitionsBuilder().with_test_data().validate())
        ).validate()

        model = yaml_model_factory(configuration=_asset_to_stream(asset), resources={})

        with pytest.raises(ModelValidationException) as exc_info:
            model.get_process_simulations(ecalc_event_service=EcalcEventService(ecalc_events=[]))

        assert str(exc_info.value) == snapshot("""\
Validation error

	Object starting on line 52
	Location: PROCESS_SIMULATIONS.my_sim
	Message: Invalid process reference 'nonexistent_stream'. Available references: fuel, train_1, my_sim
""")


class TestPipelineEventRefNotFound:
    """Tests for when a pipeline event references a process event that doesn't exist."""

    @pytest.mark.snapshot
    @pytest.mark.inlinesnapshot
    def test_pipeline_event_ref_not_found(self, yaml_model_factory):
        """A pipeline event with a ref that doesn't match any known process event
        should produce a clear error."""
        compressor_def = YamlCompressorBuilder().with_test_data().validate()

        event = YamlPipelineEvent(
            type=PipelineEventAction.CHANGE,
            change_target="stage_1",
            change_from=compressor_def,
            change_to=compressor_def,
            change_type=PipelineEventChangeType.REBUNDLE,
            ref="nonexistent_event",
        )

        pipeline = (
            YamlProcessPipelineBuilder()
            .with_name("train_1")
            .with_item(target=YamlPressureDropperBuilder().with_test_data().validate(), name="dropper")
            .with_item(target=compressor_def, name="stage_1")
            .with_events([event])
            .validate()
        )

        simulation = (
            YamlProcessSimulationBuilder()
            .with_name("my_sim")
            .with_pipeline(pipeline)
            .with_stream_distribution(YamlCommonStreamDistributionBuilder().with_test_data().validate())
        ).validate()

        asset = (
            YamlAssetBuilder()
            .with_test_data()
            .with_process_pipelines({"train_1": pipeline})
            .with_process_simulations([simulation])
            .with_definitions(YamlDefinitionsBuilder().with_test_data().validate())
        ).validate()

        model = yaml_model_factory(configuration=_asset_to_stream(asset), resources={})

        with pytest.raises(ModelValidationException) as exc_info:
            model.get_process_simulations(ecalc_event_service=EcalcEventService(ecalc_events=[]))

        assert str(exc_info.value) == snapshot("""\
Validation error

	Object starting on line 114
	Location: PROCESS_SIMULATIONS.my_sim
	Message: Pipeline event 'nonexistent_event' does not match any known process event.
""")


class TestOverflowReferenceNotFound:
    """Tests for when overflow from_reference or to_reference doesn't match a target pipeline."""

    @pytest.mark.snapshot
    @pytest.mark.inlinesnapshot
    def test_overflow_to_reference_not_found(self, yaml_model_factory):
        """An overflow with a to_reference that doesn't match any target pipeline
        should produce a clear error."""
        pipeline = _build_pipeline("train_1")

        overflow = YamlOverflow(from_reference="train_1", to_reference="nonexistent_pipeline")
        stream_distribution = (
            YamlCommonStreamDistributionBuilder().with_test_data().with_rate_fractions([1.0], overflow=[overflow])
        ).validate()

        simulation = (
            YamlProcessSimulationBuilder()
            .with_name("my_sim")
            .with_pipeline(pipeline)
            .with_stream_distribution(stream_distribution)
        ).validate()

        asset = (
            YamlAssetBuilder()
            .with_test_data()
            .with_process_pipelines({"train_1": pipeline})
            .with_process_simulations([simulation])
            .with_definitions(YamlDefinitionsBuilder().with_test_data().validate())
        ).validate()

        model = yaml_model_factory(configuration=_asset_to_stream(asset), resources={})

        with pytest.raises(ModelValidationException) as exc_info:
            model.get_process_simulations(ecalc_event_service=EcalcEventService(ecalc_events=[]))

        assert str(exc_info.value) == snapshot("""\
Validation error

	Object starting on line 52
	Location: PROCESS_SIMULATIONS.my_sim
	Message: Invalid process reference 'nonexistent_pipeline'. Available references: fuel, train_1, my_sim
""")

    @pytest.mark.snapshot
    @pytest.mark.inlinesnapshot
    def test_overflow_from_reference_not_found(self, yaml_model_factory):
        """An overflow with a from_reference that doesn't match any target pipeline
        should produce a clear error."""
        pipeline = _build_pipeline("train_1")

        overflow = YamlOverflow(from_reference="nonexistent_pipeline", to_reference="train_1")
        stream_distribution = (
            YamlCommonStreamDistributionBuilder().with_test_data().with_rate_fractions([1.0], overflow=[overflow])
        ).validate()

        simulation = (
            YamlProcessSimulationBuilder()
            .with_name("my_sim")
            .with_pipeline(pipeline)
            .with_stream_distribution(stream_distribution)
        ).validate()

        asset = (
            YamlAssetBuilder()
            .with_test_data()
            .with_process_pipelines({"train_1": pipeline})
            .with_process_simulations([simulation])
            .with_definitions(YamlDefinitionsBuilder().with_test_data().validate())
        ).validate()

        model = yaml_model_factory(configuration=_asset_to_stream(asset), resources={})

        with pytest.raises(ModelValidationException) as exc_info:
            model.get_process_simulations(ecalc_event_service=EcalcEventService(ecalc_events=[]))

        assert str(exc_info.value) == snapshot("""\
Validation error

	Object starting on line 52
	Location: PROCESS_SIMULATIONS.my_sim
	Message: Invalid process reference 'nonexistent_pipeline'. Available references: fuel, train_1, my_sim
""")
