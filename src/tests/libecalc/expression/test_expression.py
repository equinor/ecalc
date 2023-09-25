import datetime

import pytest
from libecalc.expression import Expression
from pydantic import parse_obj_as


class TestExpression:
    def test_with_operators(self):
        expression1 = Expression.setup_from_expression(value="SIM1;OIL_PROD {+} SIM1;GAS_PROD {/} 1000")
        expression2 = Expression.setup_from_expression(value="(SIM1;OIL_PROD) {+} (SIM1;GAS_PROD {/} 1000)")
        expression3 = Expression.setup_from_expression(value="(SIM1;OIL_PROD) {*} (SIM1;GAS_PROD {/} 1000)")
        expression4 = Expression.setup_from_expression(value="(SIM1;OIL_PROD) {*} (SIM1;GAS_PROD {+} 1000)")
        assert str(expression1) == "SIM1;OIL_PROD {+} SIM1;GAS_PROD {/} 1000.0"
        assert str(expression2) == "(SIM1;OIL_PROD) {+} (SIM1;GAS_PROD {/} 1000.0)"
        assert str(expression3) == "(SIM1;OIL_PROD) {*} (SIM1;GAS_PROD {/} 1000.0)"
        assert str(expression4) == "(SIM1;OIL_PROD) {*} (SIM1;GAS_PROD {+} 1000.0)"

    def test_simple(self):
        Expression.setup_from_expression(value="SIM1;OIL_PROD")

    def test_constant(self):
        Expression.setup_from_expression(value="1.0")

    def test_pydantic_parse(self):
        expression = parse_obj_as(Expression, "SIM1;OIL_PROD")
        assert expression == Expression.setup_from_expression(value="SIM1;OIL_PROD")

    def test_expressions_with_scientific_notation(self):
        expression_as_number = 0.000006
        expression_as_string_directly = "6e-06"
        expression_setup_with_numeric_input = Expression.setup_from_expression(value=expression_as_number)
        expression_setup_with_string_input = Expression.setup_from_expression(value=str(expression_as_number))
        expression_setup_with_string_directly = Expression.setup_from_expression(value=expression_as_string_directly)
        assert expression_setup_with_numeric_input.tokens[0].value == expression_as_number
        assert expression_setup_with_string_input.tokens[0].value == expression_as_number
        assert expression_setup_with_string_directly.tokens[0].value == expression_as_number
        assert len(expression_setup_with_string_input.tokens) == 1
        assert len(expression_setup_with_string_directly.tokens) == 1

        # In case of the rare event that a variable or reference is named "nan" or "inf"
        expression_with_nan_as_variable_input = "timeseriesref;nan"
        expression_with_nan_as_variable = Expression.setup_from_expression(value=expression_with_nan_as_variable_input)
        assert expression_with_nan_as_variable.tokens[0].value == expression_with_nan_as_variable_input
        assert expression_with_nan_as_variable.variables[0] == expression_with_nan_as_variable_input

        expression_with_inf_as_reference_input = "inf;OIL_PROD"
        expression_with_inf_as_reference = Expression.setup_from_expression(
            value=expression_with_inf_as_reference_input
        )
        assert expression_with_inf_as_reference.tokens[0].value == expression_with_inf_as_reference_input
        assert expression_with_inf_as_reference.variables[0] == expression_with_inf_as_reference_input

    def test_expression(self, caplog):
        variables = {"ref": [1]}
        time_vector = [datetime.datetime(2000, 1, 1)]
        assert Expression.setup_from_expression(5).evaluate(variables=variables, fill_length=len(time_vector)) == 5
        assert (
            Expression.setup_from_expression("(5{+}4){*}2").evaluate(variables=variables, fill_length=len(time_vector))
            == 18
        )
        assert (
            Expression.setup_from_expression("(5>4){+}(3>=3)").evaluate(
                variables=variables, fill_length=len(time_vector)
            )
            == 2
        )
        assert (
            Expression.setup_from_expression("(5{+}4)==9").evaluate(variables=variables, fill_length=len(time_vector))
            == 1
        )

        # Test different "illegal" eval strings
        caplog.set_level("CRITICAL")
        with pytest.raises(KeyError):
            Expression.setup_from_expression("(5{+}4)=9")
        with pytest.raises(KeyError):
            Expression.setup_from_expression("(5+4)=9")
        with pytest.raises(KeyError):
            Expression.setup_from_expression("(5-4)=9")
        with pytest.raises(KeyError):
            Expression.setup_from_expression("(5*4)=9")
        with pytest.raises(KeyError):
            Expression.setup_from_expression("(5/4)=9")
        with pytest.raises(KeyError):
            Expression.setup_from_expression("(5^4)=9")
        with pytest.raises(ValueError):
            Expression.setup_from_expression("((3{+}4){/}2{*}) {+} 2").evaluate(
                variables=variables, fill_length=len(time_vector)
            )
        with pytest.raises(ValueError):
            Expression.setup_from_expression(
                "((FULL;GAS_LIFT {+} FULL;GAS_INJ){/}FULL;REGULARITY){*} (((FULL;GAS_LIFT {+} FULL;GAS_INJ){/}FULL;REGULARITY)<8200000) {+} (8200000){*} (((FULL;GAS_LIFT {+} FULL;GAS_INJ){/}FULL;REGULARITY)>8200000)",
            ).evaluate(variables=variables, fill_length=len(time_vector))
        with pytest.raises(ValueError):
            Expression.setup_from_expression("(3{+}4){/}2{*} {+} 2").evaluate(
                variables=variables, fill_length=len(time_vector)
            )
        with pytest.raises(ValueError):
            Expression.setup_from_expression("{/}4").evaluate(variables=variables, fill_length=len(time_vector))
        with pytest.raises(ValueError):
            Expression.setup_from_expression("4{^}").evaluate(variables=variables, fill_length=len(time_vector))

    def test_invalid_key(self, caplog):
        variables = {"key_not_present": [1]}
        time_vector = [datetime.datetime(2000, 1, 1)]
        caplog.set_level("CRITICAL")
        with pytest.raises(ValueError):
            Expression.setup_from_expression("GAS_INJ_TOTAL:GRP").evaluate(
                variables=variables, fill_length=len(time_vector)
            )
        with pytest.raises(ValueError):
            Expression.setup_from_expression("SIM2;GAS_INJ_TOTAL:GRP").evaluate(
                variables=variables, fill_length=len(time_vector)
            )

        with pytest.raises(ValueError):
            expression = "SIM1;GAS_INJ_TOTAL:FOOBAR {*} 2"
            Expression.setup_from_expression(expression).evaluate(variables=variables, fill_length=len(time_vector))

        # Check that nan is handled correctly when division by zero occur, but
        # values are later disregarded by conditions
        assert (
            Expression.setup_from_expression("0{/}0").evaluate(variables=variables, fill_length=len(time_vector)) == 0
        )

        with pytest.raises(ValueError):
            Expression.setup_from_expression(
                "10 {+} 1 {+} 5)  {*} (2>0)",
            ).evaluate(variables=variables, fill_length=len(time_vector))

        with pytest.raises(ValueError):
            Expression.setup_from_expression(
                "(10 {+} 1 {+} 5  {*} (2>0)",
            ).evaluate(variables=variables, fill_length=len(time_vector))

        with pytest.raises(ValueError):
            Expression.setup_from_expression(
                "(10 {+} 1 {+} 5 ) {*} (2>0",
            ).evaluate(variables=variables, fill_length=len(time_vector))
        with pytest.raises(ValueError):
            Expression.setup_from_expression(
                "(10 {+} 1 {+} ( 5  {*} 2>0)",
            ).evaluate(variables=variables, fill_length=len(time_vector))

    def test_expression_add_variable_references(self):
        variables = {
            "$var.first": [1, 2, 3],
            "$var.second": [1, 2, 3],
        }
        assert Expression.setup_from_expression("$var.first {+} $var.second").evaluate(
            variables, fill_length=3
        ).tolist() == [2, 4, 6]
