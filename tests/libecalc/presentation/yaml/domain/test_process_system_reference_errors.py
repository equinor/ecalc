from io import StringIO

import pytest

from libecalc.ecalc_model.ecalc_event import EcalcEventService
from libecalc.presentation.yaml.model_validation_exception import ModelValidationException
from libecalc.presentation.yaml.yaml_entities import ResourceStream
from libecalc.presentation.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel
from libecalc.presentation.yaml.yaml_types.process.yaml_process_pipeline import (
    PipelineEventAction,
    PipelineEventChangeType,
    YamlPipelineEvent,
    YamlProcessPipeline,
)
from libecalc.testing.process_builders import (
    YamlCommonStreamDistributionBuilder,
    YamlCompressorModelChartBuilder,
    YamlDefinitionsBuilder,
    YamlInletStreamBuilder,
    YamlMixerBuilder,
    YamlProcessPipelineBuilder,
    YamlProcessSimulationBuilder,
    compressors_in,
    shaft_for,
)
from libecalc.testing.yaml_builder import YamlAssetBuilder

COMPRESSOR_MODEL = "compressor_model"


def _get_process_simulations(yaml_model_factory, pipeline: YamlProcessPipeline):
    """Map a model with the pipeline in one process simulation, read from YAML as a user's file is.
    DEFINITIONS has one compressor model, COMPRESSOR_MODEL."""
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
        .with_process_pipelines({pipeline.name: pipeline})
        .with_process_simulations([simulation])
        .with_definitions(
            YamlDefinitionsBuilder()
            .with_compressor_model(COMPRESSOR_MODEL, YamlCompressorModelChartBuilder().with_test_data().validate())
            .validate()
        )
        .validate()
    )
    yaml_string = PyYamlYamlModel.dump_yaml(
        yaml_dict=asset.model_dump(serialize_as_any=True, mode="json", exclude_unset=True, by_alias=True)
    )
    model = yaml_model_factory(
        configuration=ResourceStream(name="test_model", stream=StringIO(yaml_string)), resources={}
    )
    return model.get_process_simulations(ecalc_event_service=EcalcEventService(ecalc_events=[]))


@pytest.mark.parametrize(
    "model, change_to",
    [
        pytest.param("ghost", COMPRESSOR_MODEL, id="MODEL"),
        pytest.param(COMPRESSOR_MODEL, "ghost", id="CHANGE_TO"),
    ],
)
def test_compressor_model_reference_not_found_is_reported(yaml_model_factory, model, change_to):
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

    with pytest.raises(ModelValidationException, match="'ghost' not found. Available definitions"):
        _get_process_simulations(yaml_model_factory, pipeline)


def test_definition_reference_of_wrong_type_is_reported_at_the_pipeline(yaml_model_factory):
    sidestream = YamlInletStreamBuilder().with_test_data().with_fluid(COMPRESSOR_MODEL).validate()
    pipeline = (
        YamlProcessPipelineBuilder()
        .with_name("train_1")
        .with_compressor_item(compressor="compressor_1", model=COMPRESSOR_MODEL)
        .with_item(YamlMixerBuilder().with_sidestream(sidestream).validate())
        .validate()
    )

    with pytest.raises(ModelValidationException) as exc_info:
        _get_process_simulations(yaml_model_factory, pipeline)

    [error] = exc_info.value.errors()
    assert error.location.keys == ("PROCESS_PIPELINES", "train_1")
    assert f"'{COMPRESSOR_MODEL}' resolved to type 'YamlCompressorModelChart'" in error.message
