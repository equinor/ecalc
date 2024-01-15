from datetime import datetime

import pytest
from libecalc.expression import Expression
from libecalc.presentation.yaml.yaml_types.yaml_variable import (
    YamlSingleVariable,
    YamlVariables,
)
from pydantic import TypeAdapter, ValidationError


class TestVariables:
    def test_valid_entry(self):
        assert TypeAdapter(YamlVariables).validate_python({"some_var": {"VALUE": "5.0"}}) == {
            "some_var": YamlSingleVariable(value=Expression.setup_from_expression("5.0"))
        }

    def test_time_variable(self):
        assert TypeAdapter(YamlVariables).validate_python(
            {"some_var": {datetime(2013, 1, 1): {"VALUE": "5.0"}, datetime(2016, 1, 1): {"VALUE": "6.0"}}},
        ) == {
            "some_var": {
                datetime(2013, 1, 1): YamlSingleVariable(value=Expression.setup_from_expression("5.0")),
                datetime(2016, 1, 1): YamlSingleVariable(value=Expression.setup_from_expression("6.0")),
            }
        }

    def test_invalid_first_character(self):
        with pytest.raises(ValidationError) as exc_info:
            TypeAdapter(YamlVariables).validate_python({"1nvalid_key": {"VALUE": 5}})

        assert "String should match pattern '^[A-Za-z][A-Za-z0-9_]*$'" in str(exc_info.value)

    def test_invalid_second_character(self):
        with pytest.raises(ValidationError) as exc_info:
            TypeAdapter(YamlVariables).validate_python({"invalid[key]": {"VALUE": 5}})

        assert "String should match pattern '^[A-Za-z][A-Za-z0-9_]*$'" in str(exc_info.value)
