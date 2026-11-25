from datetime import datetime
from io import StringIO

import pytest

from libecalc.ecalc_model.timeline_event import TimelineEventType
from libecalc.ecalc_model.timeline_phase import TimelinePhaseType
from libecalc.presentation.yaml.model_validation_exception import ModelValidationException
from libecalc.presentation.yaml.yaml_entities import ResourceStream
from libecalc.presentation.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel
from libecalc.presentation.yaml.yaml_types.process.yaml_process_pipeline import (
    PipelineEventAction,
    PipelineEventChangeType,
    YamlPipelineChange,
)
from libecalc.testing.process_builders import (
    YamlCommonStreamDistributionBuilder,
    YamlCompressorModelChartBuilder,
    YamlDefinitionsBuilder,
    YamlProcessPipelineBuilder,
    YamlProcessSimulationBuilder,
    compressors_in,
    shaft_for,
)
from libecalc.testing.yaml_builder import YamlAssetBuilder

REBUNDLE_EVENT = {"rebundle": {"TYPE": "OPERATIONAL_MEASURE", "FROM": "2021-06-01"}}


def _model_stream(
    timeline_events: dict[str, dict] = REBUNDLE_EVENT,
    timeline_phases: dict[str, dict] | None = None,
    variables: dict[str, dict] | None = None,
) -> ResourceStream:
    rebundle = YamlPipelineChange(
        type=PipelineEventAction.CHANGE,
        change_target="stage_1",
        change_to=YamlCompressorModelChartBuilder().with_test_data().validate(),
        change_type=PipelineEventChangeType.REBUNDLE,
        ref="rebundle",
    )
    pipeline = (
        YamlProcessPipelineBuilder()
        .with_name("train_1")
        .with_compressor_item(compressor="stage_1")
        .with_changes([rebundle])
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
        .with_process_pipelines([pipeline])
        .with_process_simulations([simulation])
        .with_definitions(YamlDefinitionsBuilder().with_test_data().validate())
    ).validate()
    asset_dict = asset.model_dump(serialize_as_any=True, mode="json", exclude_unset=True, by_alias=True)
    for legacy_key in ("FACILITY_INPUTS", "MODELS", "FUEL_TYPES", "INSTALLATIONS"):
        asset_dict.pop(legacy_key, None)
    asset_dict["TIMELINE"] = {"EVENTS": timeline_events}
    if timeline_phases is not None:
        asset_dict["TIMELINE"]["PHASES"] = timeline_phases
    if variables is not None:
        asset_dict["VARIABLES"] = variables
    return ResourceStream(name="test_model", stream=StringIO(PyYamlYamlModel.dump_yaml(yaml_dict=asset_dict)))


def test_pipeline_event_takes_effect_from_timeline_event(yaml_model_factory):
    model = yaml_model_factory(
        configuration=_model_stream({"rebundle": {"TYPE": "OPERATIONAL_MEASURE", "FROM": "2021-06-01"}}),
        resources={},
        nextgen=True,
    )

    [event] = model.get_timeline_events()
    assert event.type == TimelineEventType.OPERATIONAL_MEASURE
    assert event.from_when == datetime(2021, 6, 1)

    [pipeline], _ = model.get_process_simulations()
    [pipeline_event] = pipeline.get_events()
    assert pipeline_event.change_time == datetime(2021, 6, 1)


def test_timeline_phases_are_mapped(yaml_model_factory):
    model = yaml_model_factory(
        configuration=_model_stream(
            timeline_phases={"production": {"TYPE": "PRODUCTION", "WHEN": "$var.PRODUCING"}},
            variables={"PRODUCING": {"VALUE": 1}},
        ),
        resources={},
        nextgen=True,
    ).validate_for_run()

    [phase] = model.get_timeline_phases()
    assert phase.reference == "production"
    assert phase.type == TimelinePhaseType.PRODUCTION


def test_timeline_phase_with_unknown_time_series_fails(yaml_model_factory):
    model = yaml_model_factory(
        configuration=_model_stream(timeline_phases={"production": {"TYPE": "PRODUCTION", "WHEN": "SIM;GAS_PROD > 0"}}),
        resources={},
        nextgen=True,
    )

    with pytest.raises(ModelValidationException, match="SIM;GAS_PROD"):
        model.validate_for_run()


@pytest.mark.parametrize("when", ["1", 0, True])
def test_timeline_phase_without_reference_fails(yaml_model_factory, when):
    model = yaml_model_factory(
        configuration=_model_stream(timeline_phases={"production": {"TYPE": "PRODUCTION", "WHEN": when}}),
        resources={},
        nextgen=True,
    )

    with pytest.raises(ModelValidationException, match="WHEN must reference a time series or variable"):
        model.validate_for_run()
