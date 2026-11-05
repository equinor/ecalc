from datetime import datetime
from io import StringIO

from libecalc.ecalc_model.ecalc_event import EcalcEventService
from libecalc.ecalc_model.timeline_event import TimelineEventType
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
    YamlProcessPipelineBuilder,
    YamlProcessSimulationBuilder,
    compressors_in,
    shaft_for,
)
from libecalc.testing.yaml_builder import YamlAssetBuilder


def _model_stream(timeline_events: dict[str, dict]) -> ResourceStream:
    compressor = YamlCompressorBuilder().with_test_data().validate()
    rebundle = YamlPipelineEvent(
        type=PipelineEventAction.CHANGE,
        change_target="stage_1",
        change_from=compressor,
        change_to=compressor,
        change_type=PipelineEventChangeType.REBUNDLE,
        ref="rebundle",
    )
    pipeline = (
        YamlProcessPipelineBuilder()
        .with_name("train_1")
        .with_compressor_item(target=compressor, compressor="stage_1")
        .with_events([rebundle])
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
        .with_start("2019-01-01")
        .with_end("2024-01-01")
        .with_shafts([shaft_for(pipeline, name="shaft")])
        .with_compressors(compressors_in(pipeline))
        .with_process_pipelines({"train_1": pipeline})
        .with_process_simulations([simulation])
        .with_definitions(YamlDefinitionsBuilder().with_test_data().validate())
    ).validate()
    asset_dict = asset.model_dump(serialize_as_any=True, mode="json", exclude_unset=True, by_alias=True)
    for legacy_key in ("FACILITY_INPUTS", "MODELS", "FUEL_TYPES", "INSTALLATIONS"):
        asset_dict.pop(legacy_key, None)
    asset_dict["YAML_VERSION"] = 4
    asset_dict["TIMELINE"] = {"EVENTS": timeline_events}
    return ResourceStream(name="test_model", stream=StringIO(PyYamlYamlModel.dump_yaml(yaml_dict=asset_dict)))


def test_pipeline_event_takes_effect_from_timeline_event(yaml_model_factory):
    model = yaml_model_factory(
        configuration=_model_stream({"rebundle": {"TYPE": "OPERATIONAL_MEASURE", "FROM": "2021-06-01"}}),
        resources={},
    )

    [event] = model.get_timeline_events()
    assert event.type == TimelineEventType.OPERATIONAL_MEASURE
    assert event.from_date == datetime(2021, 6, 1)

    [pipeline], _ = model.get_process_simulations(ecalc_event_service=EcalcEventService(ecalc_events=[]))
    [pipeline_event] = pipeline.get_events()
    assert pipeline_event.change_time == datetime(2021, 6, 1)
