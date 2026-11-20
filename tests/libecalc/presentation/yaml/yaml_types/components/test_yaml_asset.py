import pytest
from pydantic import ValidationError

from libecalc.presentation.yaml.yaml_types.components.yaml_asset import (
    COMMON_ROOT_FIELDS,
    LEGACY_ROOT_FIELDS,
    NEXTGEN_ROOT_FIELDS,
    YamlAsset,
)
from libecalc.presentation.yaml.yaml_types.yaml_compressor import YamlCompressor
from libecalc.presentation.yaml.yaml_validation_context import YamlModelValidationContextNames
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


def _validate(data: dict, nextgen: bool | None = None) -> YamlAsset:
    context = {} if nextgen is None else {YamlModelValidationContextNames.nextgen: nextgen}
    return YamlAsset.model_validate(data, context=context)


def test_every_root_element_is_common_legacy_or_nextgen():
    classified = [*COMMON_ROOT_FIELDS, *LEGACY_ROOT_FIELDS, *NEXTGEN_ROOT_FIELDS]

    assert sorted(classified) == sorted(YamlAsset.model_fields)


@pytest.mark.parametrize(
    "nextgen, message",
    [
        (True, "not available in a NextGen model: FUEL_TYPES, INSTALLATIONS, MODELS"),
        (False, "not available in a legacy model: TIMELINE"),
    ],
)
def test_legacy_and_nextgen_elements_cannot_be_combined(nextgen: bool, message: str):
    with pytest.raises(ValidationError, match=message):
        _validate({**_legacy_data(), "TIMELINE": _nextgen_data()["TIMELINE"]}, nextgen=nextgen)


def test_nextgen_model():
    asset = _validate(_nextgen_data(), nextgen=True)

    assert asset.timeline is not None
    assert len(asset.timeline.events) == 1


def test_legacy_model():
    asset = _validate(_legacy_data(), nextgen=False)

    assert len(asset.installations) == 1


def test_root_elements_are_not_checked_without_the_flag():
    asset = _validate({**_legacy_data(), "TIMELINE": _nextgen_data()["TIMELINE"]})

    assert asset.timeline is not None
    assert len(asset.installations) == 1


def test_nextgen_flag_rejects_legacy_elements():
    with pytest.raises(ValidationError, match="not available in a NextGen model: FUEL_TYPES, INSTALLATIONS, MODELS"):
        _validate(_legacy_data(), nextgen=True)


def test_legacy_flag_rejects_nextgen_elements():
    with pytest.raises(ValidationError, match="not available in a legacy model: TIMELINE"):
        _validate(_nextgen_data(), nextgen=False)


def test_legacy_model_requires_fuel_types_and_installations():
    with pytest.raises(ValidationError, match="required in a legacy model: FUEL_TYPES, INSTALLATIONS"):
        _validate({"END": "2025-01-01"}, nextgen=False)


def test_facility_inputs_are_available_in_nextgen_models():
    asset = _validate({**_nextgen_data(), "FACILITY_INPUTS": []}, nextgen=True)

    assert asset.facility_inputs == []


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
            .with_process_pipelines({pipeline.name: pipeline})
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
        .with_process_pipelines({pipeline_1.name: pipeline_1, pipeline_2.name: pipeline_2})
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
