import pytest
from libecalc.presentation.yaml.yaml_types.facility_model.yaml_facility_model import (
    YamlGeneratorSetModel,
)
from libecalc.presentation.yaml.yaml_types.models.yaml_compressor_chart import (
    YamlSingleSpeedChart,
    YamlVariableSpeedChart,
)
from libecalc.presentation.yaml.yaml_types.time_series.yaml_time_series import (
    YamlMiscellaneousTimeSeriesCollection,
)
from libecalc.presentation.yaml.yaml_validation_context import (
    YamlModelValidationContextNames,
)
from pydantic import TypeAdapter, ValidationError


@pytest.fixture
def yaml_time_series():
    return {
        "type": "MISCELLANEOUS",
        "name": "Time_series_1",
        "extrapolation": True,
        "interpolation_type": "LEFT",
        "file": "file.csv",
    }


def pytest_generate_tests(metafunc):
    """
    Parametrize tests based on scenarios defined in class

    https://docs.pytest.org/en/7.1.x/example/parametrize.html#a-quick-port-of-testscenarios
    """
    idlist = []
    argvalues = []

    scenarios = metafunc.cls.scenarios
    argnames = list(scenarios[0][1].keys())

    for scenario in scenarios:
        idlist.append(scenario[0])
        argvalues.append(list(scenario[1].values()))
    metafunc.parametrize(argnames, argvalues, ids=idlist, scope="class")


class TestFileValidation:
    scenarios = [
        (
            "time_series",
            {
                "yaml_obj_with_file": {
                    "type": "MISCELLANEOUS",
                    "name": "Time_series_1",
                    "extrapolation": True,
                    "interpolation_type": "LEFT",
                    "file": "file.csv",
                },
                "validation_class": YamlMiscellaneousTimeSeriesCollection,
            },
        ),
        (
            "generator_set_model",
            {
                "yaml_obj_with_file": {
                    "type": "ELECTRICITY2FUEL",
                    "name": "genset_model",
                    "file": "file.csv",
                },
                "validation_class": YamlGeneratorSetModel,
            },
        ),
        (
            "single_speed_chart",
            {
                "yaml_obj_with_file": {
                    "type": "COMPRESSOR_CHART",
                    "chart_type": "SINGLE_SPEED",
                    "name": "single_speed_chart",
                    "curve": {
                        "file": "file.csv",
                    },
                },
                "validation_class": YamlSingleSpeedChart,
            },
        ),
        (
            "variable_speed_chart",
            {
                "yaml_obj_with_file": {
                    "type": "COMPRESSOR_CHART",
                    "chart_type": "VARIABLE_SPEED",
                    "name": "variable_speed_chart",
                    "curves": {
                        "file": "file.csv",
                    },
                },
                "validation_class": YamlVariableSpeedChart,
            },
        ),
    ]

    def test_missing_file(self, yaml_obj_with_file, validation_class):
        with pytest.raises(ValidationError) as exc_info:
            TypeAdapter(validation_class).validate_python(
                yaml_obj_with_file, context={YamlModelValidationContextNames.resource_file_names: []}
            )
        errors = exc_info.value.errors()
        assert len(errors) == 1
        error = errors[0]
        assert error["type"] == "resource_not_found"
        assert error["msg"] == "resource not found, got 'file.csv'"

    def test_existing_file(self, yaml_obj_with_file, validation_class):
        TypeAdapter(validation_class).validate_python(
            yaml_obj_with_file, context={YamlModelValidationContextNames.resource_file_names: ["file.csv"]}
        )
