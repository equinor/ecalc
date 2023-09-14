from datetime import datetime

import pytest
from libecalc.expression import Expression
from libecalc.input.yaml_types.yaml_variable import YamlSingleVariable, YamlVariables
from pydantic import ValidationError, parse_obj_as


class TestVariables:
    def test_valid_entry(self):
        assert parse_obj_as(YamlVariables, {"some_var": {"VALUE": "5.0"}}) == {
            "some_var": YamlSingleVariable(value=Expression.setup_from_expression("5.0"))
        }

    def test_time_variable(self):
        assert parse_obj_as(
            YamlVariables,
            {"some_var": {datetime(2013, 1, 1): {"VALUE": "5.0"}, datetime(2016, 1, 1): {"VALUE": "6.0"}}},
        ) == {
            "some_var": {
                datetime(2013, 1, 1): YamlSingleVariable(value=Expression.setup_from_expression("5.0")),
                datetime(2016, 1, 1): YamlSingleVariable(value=Expression.setup_from_expression("6.0")),
            }
        }

    def test_invalid_first_character(self):
        with pytest.raises(ValidationError) as exc_info:
            parse_obj_as(YamlVariables, {"1nvalid_key": {"VALUE": 5}})

        assert 'string does not match regex "^[A-Za-z][A-Za-z0-9_]*$"' in str(exc_info.value)

    def test_invalid_second_character(self):
        with pytest.raises(ValidationError) as exc_info:
            parse_obj_as(YamlVariables, {"invalid[key]": {"VALUE": 5}})

        assert 'string does not match regex "^[A-Za-z][A-Za-z0-9_]*$"' in str(exc_info.value)
