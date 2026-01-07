from io import StringIO

import pytest
from inline_snapshot import snapshot

from ecalc_cli.infrastructure.file_resource_service import FileResourceService
from libecalc.presentation.yaml.file_configuration_service import FileConfigurationService
from libecalc.presentation.yaml.model import YamlModel
from libecalc.presentation.yaml.model_validation_exception import ModelValidationException
from libecalc.presentation.yaml.validation_errors import Location
from libecalc.presentation.yaml.yaml_entities import ResourceStream
from libecalc.presentation.yaml.yaml_keywords import EcalcYamlKeywords


@pytest.fixture()
def yaml_resource_with_errors() -> ResourceStream:
    yaml_with_errors = """

TIME_SERIES:
    - NAME: lol

    """
    return ResourceStream(name="yaml_with_errors", stream=StringIO(yaml_with_errors))


@pytest.fixture()
def yaml_resource_with_invalid_model_reference() -> ResourceStream:
    yaml_with_errors = """

TIME_SERIES:
    - NAME: lol

MODELS:
    - NAME: fluid_model
      TYPE: FLUID
      FLUID_MODEL_TYPE: PREDEFINED
      EOS_MODEL: SRK
      GAS_TYPE: MEDIUM

INSTALLATIONS:
    - NAME: "installation1"
      FUELCONSUMERS:
        - NAME: tabular_not_existing_model
          ENERGY_USAGE_MODEL:
            TYPE: TABULATED
            ENERGYFUNCTION: not_here
        - NAME: tabular_invalid_model_reference
          ENERGY_USAGE_MODEL:
            TYPE: TABULATED
            ENERGYFUNCTION: fluid_model
    """
    return ResourceStream(name="yaml_with_invalid_model_reference", stream=StringIO(yaml_with_errors))


class TestYamlModelValidation:
    @pytest.mark.inlinesnapshot
    @pytest.mark.snapshot
    def test_invalid_yaml(self, yaml_resource_with_errors, yaml_model_factory):
        model = yaml_model_factory(configuration=yaml_resource_with_errors, resources={})
        with pytest.raises(ModelValidationException) as exc_info:
            model.validate_for_run()

        errors = exc_info.value.errors()

        assert len(errors) == 4

        assert errors[0].message == snapshot("The keyword 'type' | 'TYPE' is missing, it is required.")
        assert errors[0].location.keys == ["TIME_SERIES", 0]

        assert errors[1].message == snapshot("This keyword is missing, it is required")
        assert errors[1].location.keys == ["FUEL_TYPES"]

        assert errors[2].message == snapshot("This keyword is missing, it is required")
        assert errors[2].location.keys == ["INSTALLATIONS"]

        assert errors[3].message == snapshot("This keyword is missing, it is required")
        assert errors[3].location.keys == ["END"]

    @pytest.mark.inlinesnapshot
    @pytest.mark.snapshot
    def test_invalid_expression_token(self, minimal_model_yaml_factory, resource_service_factory):
        yaml_model = minimal_model_yaml_factory(fuel_rate="SIM1;NOTHING {+} 1")
        configuration = yaml_model.get_configuration()
        with pytest.raises(ModelValidationException) as exc_info:
            YamlModel(
                configuration=configuration,
                resource_service=resource_service_factory({}, configuration=configuration),
            ).validate_for_run()

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0].message == snapshot("Expression reference(s) SIM1;NOTHING does not exist.")

    def test_valid_cases(self, valid_example_case_yaml_case):
        configuration = FileConfigurationService(
            configuration_path=valid_example_case_yaml_case.main_file_path
        ).get_configuration()
        yaml_model = YamlModel(
            configuration=configuration,
            resource_service=FileResourceService(
                working_directory=valid_example_case_yaml_case.main_file_path.parent, configuration=configuration
            ),
        )
        yaml_model.validate_for_run()

    def test_invalid_model_reference(self, yaml_resource_with_invalid_model_reference, yaml_model_factory):
        yaml_model = yaml_model_factory(configuration=yaml_resource_with_invalid_model_reference, resources={})
        with pytest.raises(ModelValidationException) as e:
            yaml_model.validate_for_run()

        errors = e.value.errors()
        model_not_found_error = next(error for error in errors if error.message == "Model 'not_here' not found")
        assert model_not_found_error.location.keys[:4] == ["INSTALLATIONS", 0, "FUELCONSUMERS", 0]
        invalid_type_error = next(
            error for error in errors if error.message == "Model 'fluid_model' with type FLUID is not allowed"
        )
        assert invalid_type_error.location.keys[:4] == ["INSTALLATIONS", 0, "FUELCONSUMERS", 1]

    def test_no_emitters_or_fuelconsumers(
        self,
        yaml_asset_builder_factory,
        yaml_installation_builder_factory,
        yaml_asset_configuration_service_factory,
        resource_service_factory,
    ):
        """
        Test that eCalc returns error when neither fuelconsumers or venting emitters are specified.
        """
        asset = (
            yaml_asset_builder_factory()
            .with_test_data()
            .with_installations(
                [
                    yaml_installation_builder_factory()
                    .with_test_data()
                    .with_name("installation_name")
                    .with_fuel_consumers([])
                    .with_venting_emitters([])
                    .with_generator_sets([])
                    .construct()
                ]
            )
            .construct()
        )
        configuration = yaml_asset_configuration_service_factory(asset, "no consumers or emitters").get_configuration()
        model = YamlModel(
            configuration=configuration,
            resource_service=resource_service_factory({}, configuration=configuration),
        )

        with pytest.raises(ModelValidationException) as ee:
            model.validate_for_run()

        error_message = str(ee.value)

        errors = ee.value.errors()
        assert len(errors) == 1

        assert (
            f"It is required to specify at least one of the keywords {EcalcYamlKeywords.fuel_consumers}, {EcalcYamlKeywords.generator_sets} or {EcalcYamlKeywords.installation_venting_emitters} in the model."
            in error_message
        )

    @pytest.mark.inlinesnapshot
    @pytest.mark.snapshot
    def test_wrong_keyword_name(self, resource_service_factory, configuration_service_factory):
        """Test custom pydantic error message for invalid keyword names."""
        configuration = configuration_service_factory(
            ResourceStream(stream=StringIO("INVALID_KEYWORD_IN_YAML: 5"), name="INVALID_MODEL")
        ).get_configuration()
        model = YamlModel(
            configuration=configuration,
            resource_service=resource_service_factory({}, configuration=configuration),
        )
        with pytest.raises(ModelValidationException) as exc:
            model.validate_for_run()

        errors = exc.value.errors()
        assert "INVALID_KEYWORD_IN_YAML" in str(exc.value)
        invalid_keyword_error = next(
            error for error in errors if error.location == Location(keys=["INVALID_KEYWORD_IN_YAML"])
        )

        assert invalid_keyword_error.message == snapshot("This is not a valid keyword")
