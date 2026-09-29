import pytest
from pydantic import ValidationError

from libecalc.presentation.yaml.yaml_types.components.yaml_asset import YamlDefinitions
from libecalc.presentation.yaml.yaml_types.process.yaml_process_pipeline import (
    YamlProcessPipeline,
    YamlShaftDrivenProcessUnitInstance,
)
from libecalc.presentation.yaml.yaml_types.yaml_shaft import YamlShaft
from libecalc.testing.process_builders import (
    YamlCompressorBuilder,
    YamlDefinitionsBuilder,
    YamlProcessPipelineBuilder,
)
from libecalc.testing.yaml_builder import YamlAssetBuilder


def _asset_builder(
    *,
    shafts: list[YamlShaft],
    definitions: YamlDefinitions,
    pipeline: YamlProcessPipeline,
) -> YamlAssetBuilder:
    return (
        YamlAssetBuilder()
        .with_end("2025-01-01")
        .with_shafts(shafts)
        .with_definitions(definitions)
        .with_process_pipelines({pipeline.name: pipeline})
    )


def _compressor_definitions() -> YamlDefinitions:
    return (
        YamlDefinitionsBuilder()
        .with_process_unit("compressor", YamlCompressorBuilder().with_test_data().validate())
        .validate()
    )


def test_shafts_default_to_empty():
    asset = YamlAssetBuilder().with_end("2025-01-01").validate()

    assert asset.shafts == []


def test_rejects_duplicate_shaft_names():
    with pytest.raises(ValidationError, match="SHAFTS names must be unique.*export_shaft"):
        (
            YamlAssetBuilder()
            .with_end("2025-01-01")
            .with_shafts([YamlShaft(name="export_shaft"), YamlShaft(name="export_shaft")])
            .validate()
        )


def test_maps_same_shaft_to_multiple_compressor_process_units():
    pipeline = YamlProcessPipeline.model_validate(
        {
            "NAME": "export_pipeline",
            "PROCESS_UNITS": [
                {"NAME": "lp_compressor", "TARGET": "compressor", "SHAFT": "export_shaft"},
                {"NAME": "hp_compressor", "TARGET": "compressor", "SHAFT": "export_shaft"},
            ],
        }
    )
    asset = _asset_builder(
        shafts=[YamlShaft(name="export_shaft")],
        definitions=_compressor_definitions(),
        pipeline=pipeline,
    ).validate()

    process_units = asset.process_pipelines["export_pipeline"].process_units
    shaft_driven_units = [
        process_unit for process_unit in process_units if isinstance(process_unit, YamlShaftDrivenProcessUnitInstance)
    ]
    assert [process_unit.shaft for process_unit in shaft_driven_units] == ["export_shaft", "export_shaft"]


def test_rejects_unknown_shaft_reference():
    pipeline = (
        YamlProcessPipelineBuilder()
        .with_name("export_pipeline")
        .with_shaft_driven_item(name="compressor", target="compressor", shaft="missing_shaft")
        .validate()
    )

    with pytest.raises(ValidationError, match="references unknown shaft 'missing_shaft'"):
        _asset_builder(
            shafts=[YamlShaft(name="export_shaft")],
            definitions=_compressor_definitions(),
            pipeline=pipeline,
        ).validate()


def test_rejects_multiple_shafts_in_same_process_target():
    with pytest.raises(ValidationError, match="multiple shafts: export_shaft, injection_shaft"):
        (
            YamlProcessPipelineBuilder()
            .with_name("export_pipeline")
            .with_shaft_driven_item(name="lp_compressor", target="compressor", shaft="export_shaft")
            .with_shaft_driven_item(name="hp_compressor", target="compressor", shaft="injection_shaft")
            .validate()
        )
