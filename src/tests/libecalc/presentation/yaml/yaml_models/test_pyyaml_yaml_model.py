from io import StringIO

import pytest

from libecalc.presentation.yaml.validation_errors import DtoValidationError
from libecalc.presentation.yaml.yaml_entities import ResourceStream
from libecalc.presentation.yaml.yaml_models.pyyaml_yaml_model import PyYamlYamlModel
from libecalc.presentation.yaml.yaml_validation_context import (
    YamlModelValidationContextNames,
)


@pytest.fixture()
def yaml_resource_with_errors():
    yaml_with_errors = """

TIME_SERIES:
    - NAME: lol

    """
    return ResourceStream(name="yaml_with_errors", stream=StringIO(yaml_with_errors))


@pytest.fixture()
def yaml_resource_with_invalid_model_reference():
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


class TestYamlValidation:
    def test_pyyaml_validation(self, yaml_resource_with_errors):
        with pytest.raises(DtoValidationError) as exc_info:
            PyYamlYamlModel.read(yaml_resource_with_errors).validate(
                {
                    YamlModelValidationContextNames.resource_file_names: [],
                }
            )

        errors = exc_info.value.errors()

        assert len(errors) == 3

        assert "Unable to extract tag" in errors[0].message
        assert errors[0].location.keys == ["TIME_SERIES", 0]

        assert "This keyword is missing, it is required" in errors[1].message
        assert errors[1].location.keys == ["FUEL_TYPES"]

        assert "This keyword is missing, it is required" in errors[2].message
        assert errors[2].location.keys == ["INSTALLATIONS"]

    def test_invalid_expression_token(self, minimal_model_yaml_factory):
        yaml_model = minimal_model_yaml_factory(fuel_rate="SIM1;NOTHING {+} 1")
        with pytest.raises(DtoValidationError) as exc_info:
            PyYamlYamlModel.read(ResourceStream(name=yaml_model.name, stream=StringIO(yaml_model.source))).validate(
                {YamlModelValidationContextNames.expression_tokens: []}
            )

        errors = exc_info.value.errors()
        assert len(errors) == 1
        assert errors[0].message == "Expression reference(s) SIM1;NOTHING does not exist."

    def test_expression_token_validation_ignored_if_no_context(self, minimal_model_yaml_factory):
        yaml_model = minimal_model_yaml_factory(fuel_rate="SIM1;NOTHING {+} 1")
        PyYamlYamlModel.read(ResourceStream(name=yaml_model.name, stream=StringIO(yaml_model.source))).validate({})

    def test_valid_cases(self, valid_example_case_yaml_case):
        yaml_model = PyYamlYamlModel.read(
            ResourceStream(
                name=valid_example_case_yaml_case.main_file_path.stem,
                stream=valid_example_case_yaml_case.main_file,
            )
        )
        yaml_model.validate(
            {
                YamlModelValidationContextNames.resource_file_names: list(
                    valid_example_case_yaml_case.resources.keys()
                ),
                YamlModelValidationContextNames.model_types: {
                    model.name: model for model in [*yaml_model.facility_inputs, *yaml_model.models]
                },
            }
        )

    def test_invalid_model_reference(self, yaml_resource_with_invalid_model_reference):
        yaml_model = PyYamlYamlModel.read(yaml_resource_with_invalid_model_reference)
        with pytest.raises(DtoValidationError) as e:
            yaml_model.validate(
                {
                    YamlModelValidationContextNames.resource_file_names: [],
                    YamlModelValidationContextNames.model_types: {
                        model.name: model for model in [*yaml_model.facility_inputs, *yaml_model.models]
                    },
                }
            )

        errors = e.value.errors()
        model_not_found_error = next(error for error in errors if error.message == "Model 'not_here' not found")
        assert model_not_found_error.location.keys[:4] == ["INSTALLATIONS", 0, "FUELCONSUMERS", 0]
        invalid_type_error = next(
            error for error in errors if error.message == "Model 'fluid_model' with type FLUID is not allowed"
        )
        assert invalid_type_error.location.keys[:4] == ["INSTALLATIONS", 0, "FUELCONSUMERS", 1]
