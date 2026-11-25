import pytest
from pydantic import ValidationError

from libecalc.presentation.yaml.yaml_types import YamlBase
from libecalc.presentation.yaml.yaml_types.components.yaml_asset import (
    YamlLegacyAsset,
    YamlNextgenAsset,
)
from libecalc.presentation.yaml.yaml_types.yaml_compressor import YamlCompressor
from libecalc.testing.process_builders import (
    YamlCommonStreamDistributionBuilder,
    YamlDefinitionsBuilder,
    YamlProcessPipelineBuilder,
    YamlProcessSimulationBuilder,
    YamlTimelineBuilder,
    shaft_for,
)
from libecalc.testing.yaml_builder import (
    YamlAssetBuilder,
    YamlElectricity2fuelBuilder,
    YamlLegacyAssetBuilder,
    YamlTurbineBuilder,
)

DUMP_KWARGS = {"serialize_as_any": True, "mode": "json", "exclude_unset": True, "by_alias": True}


def _legacy_data() -> dict:
    return YamlLegacyAssetBuilder().with_test_data().validate().model_dump(**DUMP_KWARGS)


def _nextgen_data() -> dict:
    timeline = YamlTimelineBuilder().with_test_data().validate().model_dump(**DUMP_KWARGS)
    return {"END": "2025-01-01", "TIMELINE": timeline}


def _forbidden_keys(error: ValidationError) -> set[str]:
    return {error["loc"][0] for error in error.errors() if error["type"] == "extra_forbidden"}


@pytest.mark.parametrize(
    "asset_type, forbidden_keys",
    [
        (YamlNextgenAsset, {"FACILITY_INPUTS", "FUEL_TYPES", "INSTALLATIONS", "MODELS"}),
        (YamlLegacyAsset, {"TIMELINE"}),
    ],
)
def test_legacy_and_nextgen_elements_cannot_be_combined(asset_type: type[YamlBase], forbidden_keys: set[str]):
    with pytest.raises(ValidationError) as exc_info:
        asset_type.model_validate({**_legacy_data(), "TIMELINE": _nextgen_data()["TIMELINE"]})

    assert _forbidden_keys(exc_info.value) == forbidden_keys


def test_nextgen_model():
    asset = YamlNextgenAsset.model_validate(_nextgen_data())

    assert asset.timeline is not None
    assert len(asset.timeline.events) == 1


def test_event_and_phase_references_must_be_unique():
    timeline = _nextgen_data()["TIMELINE"]
    timeline["PHASES"] = {"new_wells_tie_in": timeline["PHASES"]["production"]}

    with pytest.raises(
        ValidationError,
        match=r"'new_wells_tie_in' is used in more than one place: TIMELINE\.EVENTS, TIMELINE\.PHASES\.",
    ):
        _validate({**_nextgen_data(), "TIMELINE": timeline}, nextgen=True)


def test_legacy_model():
    asset = YamlLegacyAsset.model_validate(_legacy_data())

    assert len(asset.installations) == 1


def test_legacy_model_requires_fuel_types_and_installations():
    with pytest.raises(ValidationError) as exc_info:
        YamlLegacyAsset.model_validate({"END": "2025-01-01"})

    assert {(error["loc"], error["type"]) for error in exc_info.value.errors()} == {
        (("FUEL_TYPES",), "missing"),
        (("INSTALLATIONS",), "missing"),
    }


def test_pipeline_can_only_be_targeted_by_one_simulation():
    pipeline = YamlProcessPipelineBuilder().with_test_data().validate()

    simulation_1 = (
        YamlProcessSimulationBuilder()
        .with_name("simulation_1")
        .with_pipeline(pipeline)
        .with_stream_distribution(YamlCommonStreamDistributionBuilder().with_test_data().validate())
        .validate()
    )
    simulation_2 = (
        YamlProcessSimulationBuilder()
        .with_name("simulation_2")
        .with_pipeline(pipeline)
        .with_stream_distribution(YamlCommonStreamDistributionBuilder().with_test_data().validate())
        .validate()
    )

    with pytest.raises(
        ValidationError,
        match="A process pipeline can currently only be targeted by one process simulation",
    ):
        (
            YamlAssetBuilder()
            .with_test_data()
            .with_process_pipelines([pipeline])
            .with_process_simulations([simulation_1, simulation_2])
            .validate()
        )


def test_distinct_pipelines_can_each_be_targeted_by_their_own_simulation(
    yaml_process_pipeline_builder_factory,
    yaml_asset_builder_factory,
):
    pipeline_1 = (
        yaml_process_pipeline_builder_factory()
        .with_name("train_1")
        .with_compressor_item(
            compressor="compressor_1",
        )
        .validate()
    )
    pipeline_2 = (
        yaml_process_pipeline_builder_factory()
        .with_name("train_2")
        .with_compressor_item(
            compressor="compressor_2",
        )
        .validate()
    )

    simulation_1 = (
        YamlProcessSimulationBuilder()
        .with_name("simulation_1")
        .with_pipeline(pipeline_1)
        .with_stream_distribution(YamlCommonStreamDistributionBuilder().with_test_data().validate())
        .validate()
    )
    simulation_2 = (
        YamlProcessSimulationBuilder()
        .with_name("simulation_2")
        .with_pipeline(pipeline_2)
        .with_stream_distribution(YamlCommonStreamDistributionBuilder().with_test_data().validate())
        .validate()
    )

    asset = (
        yaml_asset_builder_factory()
        .with_test_data()
        .with_definitions(YamlDefinitionsBuilder().with_test_data().validate())
        .with_shafts([shaft_for(pipeline_1, name="shaft_1"), shaft_for(pipeline_2, name="shaft_2")])
        .with_compressors([YamlCompressor(name="compressor_1"), YamlCompressor(name="compressor_2")])
        .with_process_pipelines([pipeline_1, pipeline_2])
        .with_process_simulations([simulation_1, simulation_2])
        .validate()
    )

    assert [simulation.name for simulation in asset.process_simulations] == ["simulation_1", "simulation_2"]


def test_unique_references_names_colliding_sections(yaml_legacy_asset_builder_factory):
    with pytest.raises(
        ValidationError,
        match=r"'duplicated_name' is used in more than one place: FACILITY_INPUTS, MODELS\.",
    ):
        (
            yaml_legacy_asset_builder_factory()
            .with_test_data()
            .with_facility_inputs(
                [YamlElectricity2fuelBuilder().with_test_data().with_name("duplicated_name").validate()]
            )
            .with_models([YamlTurbineBuilder().with_test_data().with_name("duplicated_name").validate()])
            .validate()
        )
