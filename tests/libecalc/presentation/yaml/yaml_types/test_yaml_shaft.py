import pytest
from pydantic import ValidationError

from libecalc.presentation.yaml.yaml_types.components.yaml_asset import YamlDefinitions
from libecalc.presentation.yaml.yaml_types.energy.yaml_energy_network import YamlEnergyNetwork
from libecalc.presentation.yaml.yaml_types.process.yaml_process_pipeline import (
    YamlCompressorProcessUnitInstance,
    YamlProcessPipeline,
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


def test_rejects_duplicate_shaft_names():
    with pytest.raises(ValidationError, match="SHAFTS names must be unique. Duplicated names are: export_shaft"):
        (
            YamlAssetBuilder()
            .with_end("2025-01-01")
            .with_shafts([YamlShaft(name="export_shaft"), YamlShaft(name="export_shaft")])
            .validate()
        )


def test_maps_same_shaft_to_multiple_compressor_process_units():
    pipeline = (
        YamlProcessPipelineBuilder()
        .with_name("export_pipeline")
        .with_shaft_driven_item(name="lp_compressor", target="compressor", shaft="export_shaft")
        .with_shaft_driven_item(name="hp_compressor", target="compressor", shaft="export_shaft")
        .validate()
    )
    asset = _asset_builder(
        shafts=[YamlShaft(name="export_shaft")],
        definitions=_compressor_definitions(),
        pipeline=pipeline,
    ).validate()

    process_units = asset.process_pipelines["export_pipeline"].process_units
    shaft_driven_units = [
        process_unit for process_unit in process_units if isinstance(process_unit, YamlCompressorProcessUnitInstance)
    ]
    assert [process_unit.shaft for process_unit in shaft_driven_units] == ["export_shaft", "export_shaft"]


def test_rejects_unknown_shaft_reference():
    pipeline = (
        YamlProcessPipelineBuilder()
        .with_name("export_pipeline")
        .with_shaft_driven_item(name="compressor", target="compressor", shaft="missing_shaft")
        .validate()
    )

    with pytest.raises(
        ValidationError, match="references unknown shaft 'missing_shaft'. Available shafts in SHAFTS: export_shaft."
    ):
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


def test_rejects_same_shaft_in_multiple_process_pipelines():
    export_pipeline = (
        YamlProcessPipelineBuilder()
        .with_name("export_pipeline")
        .with_shaft_driven_item(name="export_compressor", target="compressor", shaft="common_shaft")
        .validate()
    )
    injection_pipeline = (
        YamlProcessPipelineBuilder()
        .with_name("injection_pipeline")
        .with_shaft_driven_item(name="injection_compressor", target="compressor", shaft="common_shaft")
        .validate()
    )

    with pytest.raises(
        ValidationError,
        match="Shaft 'common_shaft' is referenced by multiple process pipelines: export_pipeline, injection_pipeline",
    ):
        (
            YamlAssetBuilder()
            .with_end("2025-01-01")
            .with_shafts([YamlShaft(name="common_shaft")])
            .with_definitions(_compressor_definitions())
            .with_process_pipelines({"export_pipeline": export_pipeline, "injection_pipeline": injection_pipeline})
            .validate()
        )


def test_rejects_compressors_without_shaft(yaml_process_pipeline_builder_factory, yaml_compressor_builder_factory):
    with pytest.raises(ValidationError):
        (
            yaml_process_pipeline_builder_factory()
            .with_name("export_pipeline")
            .with_shaft_driven_item(name="lp_compressor", target="compressor", shaft="export_shaft")
            .with_item(name="hp_compressor", target=yaml_compressor_builder_factory().with_test_data().validate())
            .validate()
        )


def test_rejects_unknown_shaft_reference_from_drive_train():
    energy_network = YamlEnergyNetwork.model_validate(
        {
            "SOURCES": [{"NAME": "fuel_gas", "TYPE": "FUEL_GAS_SOURCE"}],
            "UNITS": [
                {
                    "NAME": "export_turbine",
                    "TYPE": "GAS_TURBINE",
                    "INPUT": "fuel_gas",
                    "MODEL": {"LOWER_HEATING_VALUE": 38, "CURVE": {"LOAD": [10, 20], "EFFICIENCY": [0.2, 0.3]}},
                },
                {
                    "NAME": "export_load",
                    "TYPE": "DRIVE_TRAIN",
                    "INPUT": "export_turbine",
                    "SHAFT": "missing_shaft",
                },
            ],
        }
    )

    with pytest.raises(
        ValidationError,
        match="Drive train 'export_load' references unknown shaft 'missing_shaft'. "
        "Available shafts in SHAFTS: export_shaft.",
    ):
        (
            YamlAssetBuilder()
            .with_end("2025-01-01")
            .with_shafts([YamlShaft(name="export_shaft")])
            .with_energy_network(energy_network)
            .validate()
        )


def test_rejects_same_shaft_in_multiple_drive_trains(energy_network_builder_factory):
    energy_network = (
        energy_network_builder_factory()
        .with_test_data()
        .with_gas_turbine(name="export_turbine", input="fuel_gas")
        .with_gas_turbine(name="injection_turbine", input="fuel_gas")
        .with_drive_train(name="export_load", input="export_turbine", shaft="common_shaft")
        .with_drive_train(name="injection_load", input="injection_turbine", shaft="common_shaft")
        .construct()
    )

    with pytest.raises(
        ValidationError,
        match="Shaft 'common_shaft' is referenced by multiple drive trains: export_load, injection_load",
    ):
        (
            YamlAssetBuilder()
            .with_end("2025-01-01")
            .with_shafts([YamlShaft(name="common_shaft")])
            .with_energy_network(energy_network)
            .validate()
        )
