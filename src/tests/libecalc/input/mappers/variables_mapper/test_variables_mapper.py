from datetime import datetime

import pytest

from libecalc.dto import VariablesMap
from libecalc.expression import Expression
from libecalc.presentation.yaml.mappers.variables_mapper.variables_mapper import (
    VariableProcessor,
    _evaluate_variables,
)
from libecalc.presentation.yaml.yaml_types.yaml_variable import YamlSingleVariable


class TestEvaluateVariables:
    def test_unsolvable(self):
        with pytest.raises(ValueError) as exc_info:
            _evaluate_variables(
                variables={
                    "test_id": YamlSingleVariable(value=Expression.setup_from_expression("SIM1;TEST")),
                    "test_id1": YamlSingleVariable(value=Expression.setup_from_expression("SIM1;TEST")),
                    "test_id2": YamlSingleVariable(value=Expression.setup_from_expression("SIM2;TEST")),
                    "test_id3": YamlSingleVariable(value=Expression.setup_from_expression("SIM3;TEST")),
                },
                variables_map=VariablesMap(variables={}, time_vector=[]),
            )
        assert str(exc_info.value) == (
            "Could not evaluate all variables, unable to resolve references in "
            "$var.test_id, $var.test_id1, $var.test_id2, $var.test_id3. Missing "
            "references are SIM1;TEST, SIM2;TEST, SIM3;TEST"
        )

    def test_two_layers(self):
        variables_map = VariablesMap(
            variables={"SIM1;TEST": [2, 4]},
            time_vector=[
                datetime(2010, 1, 1),
                datetime(2012, 1, 1),
            ],
        )
        variables = {"VAR1": YamlSingleVariable(value=Expression.setup_from_expression("SIM1;TEST {*} 2"))}
        evaluated_variables = _evaluate_variables(variables=variables, variables_map=variables_map)
        assert evaluated_variables.variables["$var.VAR1"] == [4, 8]

    def test_many_layers(self):
        test_values = [2, 4]
        variables_map = VariablesMap(
            variables={"SIM1;TEST": test_values},
            time_vector=[
                datetime(2010, 1, 1),
                datetime(2012, 1, 1),
            ],
        )
        variables = {
            "VAR5": YamlSingleVariable(value=Expression.setup_from_expression("$var.VAR4 {*} 2")),
            "VAR2": YamlSingleVariable(value=Expression.setup_from_expression("$var.VAR1 {*} 2")),
            "VAR1": YamlSingleVariable(value=Expression.setup_from_expression("SIM1;TEST {*} 2")),
            "VAR4": YamlSingleVariable(value=Expression.setup_from_expression("$var.VAR3 {*} 2")),
            "VAR3": YamlSingleVariable(value=Expression.setup_from_expression("$var.VAR2 {*} 2")),
        }
        evaluated_variables = _evaluate_variables(variables=variables, variables_map=variables_map)
        for n in range(1, 5):
            expected_values = [value * 2**n for value in test_values]
            assert evaluated_variables.variables[f"$var.VAR{n}"] == expected_values

    @pytest.mark.skip("deactivate caplog tests for now")
    def test_time_variable(self, caplog):
        test_values = [2, 4, 6]
        variables_map = VariablesMap(
            variables={"SIM1;TEST": test_values},
            time_vector=[datetime(2010, 1, 1), datetime(2012, 1, 1), datetime(2015, 1, 1)],
        )
        variables = {
            "VAR1": {
                datetime(2012, 1, 1): YamlSingleVariable(value=Expression.setup_from_expression("SIM1;TEST {*} 2")),
                datetime(2015, 1, 1): YamlSingleVariable(value=Expression.setup_from_expression("2")),
            }
        }

        evaluated_variables = _evaluate_variables(variables=variables, variables_map=variables_map)

        assert evaluated_variables == VariablesMap(
            variables={
                "SIM1;TEST": [2, 4, 6],
                "$var.VAR1": [0, 8, 2],
            },
            time_vector=variables_map.time_vector,
        )
        assert "Variable $var.VAR1 is not defined for all time steps. Using 0.0 as fill value." in caplog.text


class TestVariableProcessor:
    def test_process_time_variable_without_references(self):
        time_vector = [datetime(2010, 1, 1), datetime(2012, 1, 1), datetime(2015, 1, 1)]
        processor = VariableProcessor(
            reference_id="$var.test",
            variable={
                datetime(2010, 1, 1): YamlSingleVariable(value=Expression.setup_from_expression("2")),
            },
        )
        assert processor.process(variables={}, time_vector=time_vector) == [2.0, 2.0, 2.0]
