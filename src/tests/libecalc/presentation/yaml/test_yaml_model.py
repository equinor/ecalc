from io import StringIO

import pytest

from ecalc_cli.infrastructure.file_resource_service import FileResourceService
from libecalc.common.time_utils import Frequency
from libecalc.presentation.yaml.file_configuration_service import FileConfigurationService
from libecalc.presentation.yaml.model import YamlModel
from libecalc.presentation.yaml.model_validation_exception import ModelValidationException
from libecalc.presentation.yaml.yaml_entities import ResourceStream


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
    def test_pyyaml_validation(self, yaml_resource_with_errors, yaml_model_factory):
        model = yaml_model_factory(resource_stream=yaml_resource_with_errors, resources={})
        with pytest.raises(ModelValidationException) as exc_info:
            model.validate_for_run()

        errors = exc_info.value.errors()

        assert len(errors) == 3

        assert "Unable to extract tag" in errors[0].message
        assert errors[0].location.keys == ["TIME_SERIES", 0]

        assert "This keyword is missing, it is required" in errors[1].message
        assert errors[1].location.keys == ["FUEL_TYPES"]

        assert "This keyword is missing, it is required" in errors[2].message
        assert errors[2].location.keys == ["INSTALLATIONS"]

    def test_invalid_expression_token(self, minimal_model_yaml_factory, resource_service_factory):
        yaml_model = minimal_model_yaml_factory(fuel_rate="SIM1;NOTHING {+} 1")
        with pytest.raises(ModelValidationException) as exc_info:
            YamlModel(
                configuration_service=yaml_model,
                resource_service=resource_service_factory({}),
                output_frequency=Frequency.NONE,
            ).validate_for_run()

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0].message == "Expression reference(s) SIM1;NOTHING does not exist."

    def test_valid_cases(self, valid_example_case_yaml_case):
        yaml_model = YamlModel(
            configuration_service=FileConfigurationService(
                configuration_path=valid_example_case_yaml_case.main_file_path
            ),
            resource_service=FileResourceService(working_directory=valid_example_case_yaml_case.main_file_path.parent),
            output_frequency=Frequency.NONE,
        )
        yaml_model.validate_for_run()

    def test_invalid_model_reference(self, yaml_resource_with_invalid_model_reference, yaml_model_factory):
        yaml_model = yaml_model_factory(resource_stream=yaml_resource_with_invalid_model_reference, resources={})
        with pytest.raises(ModelValidationException) as e:
            yaml_model.validate_for_run()

        errors = e.value.errors()
        model_not_found_error = next(error for error in errors if error.message == "Model 'not_here' not found")
        assert model_not_found_error.location.keys[:4] == ["INSTALLATIONS", 0, "FUELCONSUMERS", 0]
        invalid_type_error = next(
            error for error in errors if error.message == "Model 'fluid_model' with type FLUID is not allowed"
        )
        assert invalid_type_error.location.keys[:4] == ["INSTALLATIONS", 0, "FUELCONSUMERS", 1]
