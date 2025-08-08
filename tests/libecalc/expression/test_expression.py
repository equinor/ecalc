import datetime

import pytest
from inline_snapshot import snapshot
from pydantic import BaseModel, TypeAdapter

from libecalc.expression import Expression
from libecalc.expression.expression import InvalidExpressionError


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
        expression = TypeAdapter(Expression).validate_python("SIM1;OIL_PROD")
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

    @pytest.mark.parametrize(
        "expression, expected",
        [
            ("4 {^} 3 {^} 2", 262144),  # Check associativity, i.e. '4^3^2' == '4^(3^2)' -> right associativity
            ("3 {^} 3", 27),
            ("12 {*} 7", 84),
            ("10 {/} 4", 2.5),
            ("10 {*} 2 {^} 2", 40.0),
            ("12 {+} 7", 19),
            ("12 {-} 7", 5),
            ("2 {^} 4", 16.0),
            ("2 {+} 2 {^} 4 {*} 2", 34.0),
            ("12 >= 7", 1),
            ("12 < 7", 0),
            ("12 < 7 {+} 6", 1),
            ("12 {-} 7 == 5", 1),
            ("5 {+} 4 == 9", 1),
            ("5 {+} 4 != 9", 0),
            ("(5)", 5),
            (5, 5),
            ("(5 {+} 4) {*} 2", 18),
            ("(5 > 4) {+} (3 >= 3)", 2),
            ("5 > 4 {+} 3", 0),  # Test precedence, arithmetic before comparison
            ("((5 {+} 4) {*} 2 {-} 3) {+} 1", 16),
            ("5 4 {+}", 9),  # Limitation of shunting yard, unable to mark as invalid
            ("(((5 {+} 4) {+} 3 ) {+} 2)", 14),
        ],
    )
    def test_expressions(self, expression, expected):
        assert Expression.setup_from_expression(expression).evaluate({}, 1)[0] == expected

    @pytest.mark.inlinesnapshot
    @pytest.mark.snapshot
    @pytest.mark.parametrize(
        "expression, expected",
        [
            (
                "(5{+}4)=9",
                snapshot(
                    "Invalid expression '(5{+}4)=9': 'Illegal character: \"=\" in \"(5{+}4)=9\". Did you forget to put {} around operators?'"
                ),
            ),
            (
                "(5+4)==9",
                snapshot(
                    "Invalid expression '(5+4)==9': 'Illegal character: \"+\" in \"(5+4)==9\". Did you forget to put {} around operators?'"
                ),
            ),
            (
                "(5-4)==9",
                snapshot(
                    "Invalid expression '(5-4)==9': 'Illegal character: \"-\" in \"(5-4)==9\". Did you forget to put {} around operators?'"
                ),
            ),
            (
                "(5*4)==9",
                snapshot(
                    "Invalid expression '(5*4)==9': 'Illegal character: \"*\" in \"(5*4)==9\". Did you forget to put {} around operators?'"
                ),
            ),
            (
                "(5/4)==9",
                snapshot(
                    "Invalid expression '(5/4)==9': 'Illegal character: \"/\" in \"(5/4)==9\". Did you forget to put {} around operators?'"
                ),
            ),
            (
                "(5^4)==9",
                snapshot(
                    "Invalid expression '(5^4)==9': 'Illegal character: \"^\" in \"(5^4)==9\". Did you forget to put {} around operators?'"
                ),
            ),
            (
                "((3{+}4){/}2{*}) {+} 2",
                snapshot(
                    "Invalid expression '((3.0 {+} 4.0) {/} 2.0 {*}) {+} 2.0': Missing right operand for operator '{*}'"
                ),
            ),
            (
                "(3{+}4){/}2{*} {+} 2",
                snapshot(
                    "Invalid expression '(3.0 {+} 4.0) {/} 2.0 {*} {+} 2.0': Missing right operand for operator '{*}'"
                ),
            ),
            (
                "{/}4",
                snapshot("Invalid expression '{/} 4.0': Missing right operand for operator '{/}'"),
            ),
            (
                "4{^}",
                snapshot("Invalid expression '4.0 {^}': Missing right operand for operator '{^}'"),
            ),
            (
                "10 {+} 1 {+} 5)  {*} (2>0)",
                snapshot(
                    "Invalid expression '10.0 {+} 1.0 {+} 5.0) {*} (2.0 > 0.0)': Number of left and right parentheses do not match"
                ),
            ),
            (
                "(10 {+} 1 {+} 5  {*} (2>0)",
                snapshot(
                    "Invalid expression '(10.0 {+} 1.0 {+} 5.0 {*} (2.0 > 0.0)': Number of left and right parentheses do not match"
                ),
            ),
            (
                "(10 {+} 1 {+} 5 ) {*} (2>0",
                snapshot(
                    "Invalid expression '(10.0 {+} 1.0 {+} 5.0) {*} (2.0 > 0.0': Number of left and right parentheses do not match"
                ),
            ),
            (
                "(10 {+} 1 {+} ( 5  {*} 2>0)",
                snapshot(
                    "Invalid expression '(10.0 {+} 1.0 {+} (5.0 {*} 2.0 > 0.0)': Number of left and right parentheses do not match"
                ),
            ),
            ("5 {+}", snapshot("Invalid expression '5.0 {+}': Missing right operand for operator '{+}'")),
            ("(5 {+})", snapshot("Invalid expression '(5.0 {+})': Missing right operand for operator '{+}'")),
        ],
    )
    def test_invalid_expressions(self, expression, expected):
        with pytest.raises(InvalidExpressionError) as exc_info:
            Expression.setup_from_expression(expression)

        assert str(exc_info.value) == expected

    @pytest.mark.inlinesnapshot
    @pytest.mark.snapshot
    @pytest.mark.parametrize(
        "expression, expected",
        [
            (
                "GAS_INJ_TOTAL:GRP",
                snapshot(
                    "Invalid expression 'GAS_INJ_TOTAL:GRP': Unable to evaluate expression. Missing reference(s) GAS_INJ_TOTAL:GRP"
                ),
            ),
            (
                "SIM2;GAS_INJ_TOTAL:GRP",
                snapshot(
                    "Invalid expression 'SIM2;GAS_INJ_TOTAL:GRP': Unable to evaluate expression. Missing reference(s) SIM2;GAS_INJ_TOTAL:GRP"
                ),
            ),
            (
                "SIM1;GAS_INJ_TOTAL:FOOBAR {*} 2",
                snapshot(
                    "Invalid expression 'SIM1;GAS_INJ_TOTAL:FOOBAR {*} 2.0': Unable to evaluate expression. Missing reference(s) SIM1;GAS_INJ_TOTAL:FOOBAR"
                ),
            ),
            (
                "((FULL;GAS_LIFT {+} FULL;GAS_INJ){/}FULL;REGULARITY){*} (((FULL;GAS_LIFT {+} FULL;GAS_INJ){/}FULL;REGULARITY)<8200000) {+} (8200000){*} (((FULL;GAS_LIFT {+} FULL;GAS_INJ){/}FULL;REGULARITY)>8200000)",
                snapshot(
                    "Invalid expression '((FULL;GAS_LIFT {+} FULL;GAS_INJ) {/} FULL;REGULARITY) {*} (((FULL;GAS_LIFT {+} FULL;GAS_INJ) {/} FULL;REGULARITY) < 8200000.0) {+} (8200000.0) {*} (((FULL;GAS_LIFT {+} FULL;GAS_INJ) {/} FULL;REGULARITY) > 8200000.0)': Unable to evaluate expression. Missing reference(s) FULL;GAS_LIFT, FULL;GAS_INJ, FULL;REGULARITY, FULL;GAS_LIFT, FULL;GAS_INJ, FULL;REGULARITY, FULL;GAS_LIFT, FULL;GAS_INJ, FULL;REGULARITY"
                ),
            ),
        ],
    )
    def test_missing_variable(self, expression, expected):
        variables = {"key_not_present": [1]}
        time_vector = [datetime.datetime(2000, 1, 1)]
        with pytest.raises(InvalidExpressionError) as exc_info:
            Expression.setup_from_expression(expression).evaluate(variables=variables, fill_length=len(time_vector))

        assert str(exc_info.value) == expected

    def test_divide_zero(self):
        # Check that nan is handled correctly when division by zero occur, but
        # values are later disregarded by conditions
        assert Expression.setup_from_expression("0{/}0").evaluate(variables={}, fill_length=1) == 0

    def test_expression_add_variable_references(self):
        variables = {
            "$var.first": [1, 2, 3],
            "$var.second": [1, 2, 3],
        }
        assert Expression.setup_from_expression("$var.first {+} $var.second").evaluate(
            variables, fill_length=3
        ).tolist() == [2, 4, 6]

    def test_serialization(self):
        class Foo(BaseModel):
            single: Expression
            list: list[Expression]
            union_list: Expression | list[Expression]

        foo = Foo(
            single=Expression.setup_from_expression("1"),
            list=[
                Expression.setup_from_expression("2"),
                Expression.setup_from_expression("2"),
            ],
            union_list=[
                Expression.setup_from_expression("2"),
                Expression.setup_from_expression("2"),
            ],
        )

        assert foo.model_dump_json() == '{"single":"1.0","list":["2.0","2.0"],"union_list":["2.0","2.0"]}'

    @pytest.mark.inlinesnapshot
    @pytest.mark.snapshot
    def test_invalid_nof_parentheses(self):
        expression = "(1 {+} 3) {+} (1 {+} 5"
        with pytest.raises(InvalidExpressionError) as exc_info:
            Expression.setup_from_expression(expression)

        assert str(exc_info.value) == snapshot(
            "Invalid expression '(1.0 {+} 3.0) {+} (1.0 {+} 5.0': Number of left and right parentheses do not match"
        )
