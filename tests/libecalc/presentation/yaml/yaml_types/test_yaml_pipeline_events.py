import pytest
from pydantic import ValidationError

from libecalc.presentation.yaml.yaml_types.components.yaml_asset import YamlAsset
from libecalc.testing.process_builders import (
    YamlCompressorModelChartBuilder,
    YamlDefinitionsBuilder,
    YamlPressureDropperBuilder,
    YamlProcessPipelineBuilder,
    compressors_in,
    shaft_for,
)
from libecalc.testing.yaml_builder import YamlAssetBuilder


def _asset_data() -> dict:
    """A valid model as a YAML dict, so a test can add an event and validate it like a user's file."""
    train_a = (
        YamlProcessPipelineBuilder()
        .with_name("train_a")
        .with_compressor_item(compressor="comp_a", model="model_a")
        .with_item(name="my_dropper", target=YamlPressureDropperBuilder().with_test_data().validate())
        .validate()
    )
    train_b = (
        YamlProcessPipelineBuilder()
        .with_name("train_b")
        .with_compressor_item(compressor="comp_b", model="model_a")
        .validate()
    )
    asset = (
        YamlAssetBuilder()
        .with_end("2025-01-01")
        .with_definitions(
            YamlDefinitionsBuilder()
            .with_compressor_model("model_a", YamlCompressorModelChartBuilder().with_test_data().validate())
            .with_compressor_model("model_b", YamlCompressorModelChartBuilder().with_test_data().validate())
            .validate()
        )
        .with_shafts([shaft_for(train_a, name="shaft_a"), shaft_for(train_b, name="shaft_b")])
        .with_compressors(compressors_in(train_a, train_b))
        .with_process_pipelines({"train_a": train_a, "train_b": train_b})
        .validate()
    )
    return asset.model_dump(serialize_as_any=True, mode="json", exclude_unset=True, by_alias=True)


def _with_rebundle(change_target: str, change_to: str | dict) -> dict:
    data = _asset_data()
    data["PROCESS_PIPELINES"]["train_a"]["EVENTS"] = [
        {
            "TYPE": "CHANGE",
            "CHANGE_TARGET": change_target,
            "CHANGE_TO": change_to,
            "CHANGE_TYPE": "REBUNDLE",
            "REF": "rebundle",
        }
    ]
    return data


@pytest.mark.parametrize(
    "change_target",
    [
        pytest.param("ghost", id="unknown name"),
        pytest.param("comp_b", id="compressor in another pipeline"),
        pytest.param("my_dropper", id="non-compressor unit"),
    ],
)
def test_rejects_rebundle_not_targeting_a_compressor_in_the_pipeline(change_target):
    with pytest.raises(
        ValidationError,
        match=f"REBUNDLE event targets '{change_target}', which is not a compressor in pipeline 'train_a'. "
        "Compressors in this pipeline: comp_a.",
    ):
        YamlAsset.model_validate(_with_rebundle(change_target=change_target, change_to="model_b"))
