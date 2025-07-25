import itertools
from dataclasses import dataclass

import pytest
from inline_snapshot import snapshot

from libecalc.common.time_utils import Frequency
from libecalc.presentation.yaml.model import YamlModel
from libecalc.presentation.yaml.model_validation_exception import ModelValidationException
from libecalc.testing.facility_resource_factories import el2fuel_factory
from libecalc.testing.time_series_factories import production_profile_factory
from libecalc.testing.yaml_builder import (
    YamlAssetBuilder,
    YamlElectricity2fuelBuilder,
    YamlElectricityConsumerBuilder,
    YamlFuelConsumerBuilder,
    YamlFuelTypeBuilder,
    YamlGeneratorSetBuilder,
    YamlInstallationBuilder,
    YamlTimeSeriesBuilder,
    YamlTurbineBuilder,
    YamlVentingEmitterOilTypeBuilder,
)


@pytest.fixture
def duplicate_genset_name_model(
    yaml_asset_configuration_service_factory,
    resource_service_factory,
):
    el2fuel_reference = "el2fuel"
    el2fuel_resource_reference = "el2fuel_file"
    model = (
        YamlAssetBuilder()
        .with_test_data()
        .with_facility_inputs(
            [
                YamlElectricity2fuelBuilder()
                .with_test_data()
                .with_name(el2fuel_reference)
                .with_file(el2fuel_resource_reference)
                .validate()
            ]
        )
        .with_installations(
            [
                YamlInstallationBuilder()
                .with_test_data()
                .with_generator_sets(
                    [
                        YamlGeneratorSetBuilder()
                        .with_test_data()
                        .with_name("genset1")
                        .with_electricity2fuel(el2fuel_reference)
                        .with_consumers([YamlElectricityConsumerBuilder().with_test_data().with_name("el1").validate()])
                        .construct(),
                        YamlGeneratorSetBuilder()
                        .with_test_data()
                        .with_name("genset1")
                        .with_electricity2fuel(el2fuel_reference)
                        .with_consumers([YamlElectricityConsumerBuilder().with_test_data().with_name("el2").validate()])
                        .construct(),
                    ]
                )
                .with_fuel_consumers([YamlFuelConsumerBuilder().with_test_data().validate()])
                .construct(),
            ]
        )
        .construct()
    )
    configuration = yaml_asset_configuration_service_factory(model, name="invalid_model").get_configuration()

    return YamlModel(
        configuration=configuration,
        resource_service=resource_service_factory(
            {el2fuel_resource_reference: el2fuel_factory()}, configuration=configuration
        ),
        output_frequency=Frequency.NONE,
    )


@pytest.mark.snapshot
@pytest.mark.inlinesnapshot
def test_genset_duplicate_names(duplicate_genset_name_model):
    with pytest.raises(ModelValidationException) as exc_info:
        duplicate_genset_name_model.validate_for_run()

    errors = exc_info.value.errors()
    assert len(errors) == 1
    assert errors[0].message == snapshot(
        "Value error, Component names must be unique. Components include the main model, installations, generator sets, electricity consumers, fuel consumers, systems and its consumers and direct emitters. Duplicated names are: genset1"
    )


@dataclass
class DuplicateComponents:
    genset: bool
    electricity_consumer: bool
    fuel_consumer: bool
    venting_emitter: bool
    installation: bool
    asset: bool


def generate_model(
    duplicate_components: DuplicateComponents,
    yaml_asset_configuration_service_factory,
    resource_service_factory,
    duplicate_name: str,
) -> YamlModel:
    def get_name(component_type: str):
        should_duplicate = getattr(duplicate_components, component_type)
        return duplicate_name if should_duplicate else f"{component_type}1"

    el2fuel_reference = "el2fuel"
    el2fuel_resource_reference = "el2fuel_file"
    model = (
        YamlAssetBuilder()
        .with_test_data()
        .with_facility_inputs(
            [
                YamlElectricity2fuelBuilder()
                .with_test_data()
                .with_name(el2fuel_reference)
                .with_file(el2fuel_resource_reference)
                .validate()
            ]
        )
        .with_installations(
            [
                YamlInstallationBuilder()
                .with_test_data()
                .with_name(get_name("installation"))
                .with_generator_sets(
                    [
                        YamlGeneratorSetBuilder()
                        .with_test_data()
                        .with_name(get_name("genset"))
                        .with_electricity2fuel(el2fuel_reference)
                        .with_consumers(
                            [
                                YamlElectricityConsumerBuilder()
                                .with_test_data()
                                .with_name(get_name("electricity_consumer"))
                                .validate()
                            ]
                        )
                        .validate(),
                    ]
                )
                .with_fuel_consumers(
                    [YamlFuelConsumerBuilder().with_test_data().with_name(get_name("fuel_consumer")).validate()]
                )
                .with_venting_emitters(
                    [
                        YamlVentingEmitterOilTypeBuilder()
                        .with_test_data()
                        .with_name(get_name("venting_emitter"))
                        .validate()
                    ]
                )
                .construct(),
            ]
        )
        .construct()
    )
    configuration = yaml_asset_configuration_service_factory(model, name=get_name("asset")).get_configuration()

    return YamlModel(
        configuration=configuration,
        resource_service=resource_service_factory(
            {el2fuel_resource_reference: el2fuel_factory()}, configuration=configuration
        ),
        output_frequency=Frequency.NONE,
    )


@pytest.mark.snapshot
@pytest.mark.inlinesnapshot
@pytest.mark.parametrize(
    "first_duplicate, second_duplicate",
    itertools.combinations(
        ("genset", "electricity_consumer", "fuel_consumer", "venting_emitter", "installation", "asset"), 2
    ),
)
def test_duplicate_names_combinations(
    first_duplicate, second_duplicate, yaml_asset_configuration_service_factory, resource_service_factory
):
    duplicate_names = DuplicateComponents(
        genset="genset" in [first_duplicate, second_duplicate],
        electricity_consumer="electricity_consumer" in [first_duplicate, second_duplicate],
        fuel_consumer="fuel_consumer" in [first_duplicate, second_duplicate],
        venting_emitter="venting_emitter" in [first_duplicate, second_duplicate],
        installation="installation" in [first_duplicate, second_duplicate],
        asset="asset" in [first_duplicate, second_duplicate],
    )
    model = generate_model(
        duplicate_names,
        yaml_asset_configuration_service_factory,
        resource_service_factory,
        duplicate_name="duplicationedness",
    )
    with pytest.raises(ModelValidationException) as exc_info:
        model.validate_for_run()

    errors = exc_info.value.errors()
    assert len(errors) == 1
    assert errors[0].message == snapshot(
        "Value error, Component names must be unique. Components include the main model, installations, generator sets, electricity consumers, fuel consumers, systems and its consumers and direct emitters. Duplicated names are: duplicationedness"
    )


@pytest.mark.inlinesnapshot
@pytest.mark.snapshot
def test_fuel_types_unique_name(yaml_asset_configuration_service_factory, resource_service_factory):
    """
    TEST SCOPE: Check that duplicate fuel type names are not allowed.

    Duplicate fuel type names should not be allowed across installations.
    Duplicate names may lead to debug problems and overriding of previous
    values without user noticing. This test checks that different fuels cannot
    have same name.
    """
    model = (
        YamlAssetBuilder()
        .with_test_data()
        .with_fuel_types(
            [
                YamlFuelTypeBuilder().with_test_data().with_name("same").construct(),
                YamlFuelTypeBuilder().with_test_data().with_name("same").construct(),
            ]
        )
        .construct()
    )
    configuration = yaml_asset_configuration_service_factory(model, "non_unique_fuel_names").get_configuration()
    yaml_model = YamlModel(
        configuration=configuration,
        resource_service=resource_service_factory({}, configuration=configuration),
        output_frequency=Frequency.NONE,
    )
    with pytest.raises(ModelValidationException) as exc_info:
        yaml_model.validate_for_run()

    errors = exc_info.value.errors()
    assert len(errors) == 1
    assert errors[0].message == snapshot("Value error, FUEL_TYPES names must be unique. Duplicated names are: same")


@pytest.mark.inlinesnapshot
@pytest.mark.snapshot
def test_timeseries_unique_name(yaml_asset_configuration_service_factory, resource_service_factory):
    """
    TEST SCOPE: Check that duplicate timeseries names are not allowed.
    """
    model = (
        YamlAssetBuilder()
        .with_test_data()
        .with_time_series(
            [
                YamlTimeSeriesBuilder().with_test_data().with_name("SIM1").validate(),
                YamlTimeSeriesBuilder().with_test_data().with_name("SIM1").validate(),
            ]
        )
        .construct()
    )
    configuration = yaml_asset_configuration_service_factory(model, "non_unique_timeseries_names").get_configuration()
    yaml_model = YamlModel(
        configuration=configuration,
        resource_service=resource_service_factory(
            {"DefaultTimeSeries.csv": production_profile_factory()}, configuration=configuration
        ),
        output_frequency=Frequency.NONE,
    )
    with pytest.raises(ModelValidationException) as exc_info:
        yaml_model.validate_for_run()

    errors = exc_info.value.errors()
    assert len(errors) == 1
    assert errors[0].message == snapshot("Value error, TIME_SERIES names must be unique. Duplicated names are: SIM1")


@pytest.mark.inlinesnapshot
@pytest.mark.snapshot
@pytest.mark.parametrize(
    "facility_inputs, models, expected_error_message",
    [
        (
            [
                YamlElectricity2fuelBuilder()
                .with_test_data()
                .with_name("duplicated_name")
                .with_file("el2fuelresource")
                .validate(),
                YamlElectricity2fuelBuilder()
                .with_test_data()
                .with_name("duplicated_name")
                .with_file("el2fuelresource")
                .validate(),
            ],
            [],
            snapshot(
                "Value error, Model names must be unique across FACILITY_INPUTS and MODELS. Duplicated names are: duplicated_name"
            ),
        ),
        (
            [
                YamlElectricity2fuelBuilder()
                .with_test_data()
                .with_name("duplicated_name")
                .with_file("el2fuelresource")
                .validate(),
            ],
            [
                YamlTurbineBuilder().with_test_data().with_name("duplicated_name").validate(),
            ],
            snapshot(
                "Value error, Model names must be unique across FACILITY_INPUTS and MODELS. Duplicated names are: duplicated_name"
            ),
        ),
        (
            [],
            [
                YamlTurbineBuilder().with_test_data().with_name("duplicated_name").validate(),
                YamlTurbineBuilder().with_test_data().with_name("duplicated_name").validate(),
            ],
            snapshot(
                "Value error, Model names must be unique across FACILITY_INPUTS and MODELS. Duplicated names are: duplicated_name"
            ),
        ),
    ],
)
def test_models_unique_name(
    facility_inputs, models, expected_error_message, yaml_asset_configuration_service_factory, resource_service_factory
):
    """
    TEST SCOPE: Check that duplicate timeseries names are not allowed.
    """
    model = YamlAssetBuilder().with_test_data().with_facility_inputs(facility_inputs).with_models(models).construct()
    configuration = yaml_asset_configuration_service_factory(model, "non_unique_model_names").get_configuration()
    yaml_model = YamlModel(
        configuration=configuration,
        resource_service=resource_service_factory({"el2fuelresource": el2fuel_factory()}, configuration=configuration),
        output_frequency=Frequency.NONE,
    )
    with pytest.raises(ModelValidationException) as exc_info:
        yaml_model.validate_for_run()

    errors = exc_info.value.errors()
    assert len(errors) == 1
    assert errors[0].message == expected_error_message
