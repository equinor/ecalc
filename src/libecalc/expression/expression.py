from __future__ import annotations

from typing import Any, Union

import numpy as np
from numpy.typing import NDArray
from pydantic import GetCoreSchemaHandler, GetJsonSchemaHandler
from pydantic.json_schema import JsonSchemaValue
from pydantic_core import CoreSchema, core_schema

from libecalc.common.errors.exceptions import EcalcError, EcalcErrorType
from libecalc.common.logger import logger
from libecalc.expression.expression_evaluator import Operators, Token, TokenTag, eval_tokens, lexer

LEFT_PARENTHESIS_TOKEN = Token(tag=TokenTag.operator, value=Operators.left_parenthesis.value)
RIGHT_PARENTHESIS_TOKEN = Token(tag=TokenTag.operator, value=Operators.right_parenthesis.value)
MULTIPLICATION_TOKEN = Token(tag=TokenTag.operator, value=Operators.multiply.value)

ExpressionType = Union[str, float, int]


class InvalidExpressionError(EcalcError):
    """
    Invalid expression error
    """

    def __init__(self, message: str):
        super().__init__(
            title="Invalid expression",
            message=message,
            error_type=EcalcErrorType.CLIENT_ERROR,
        )


class Expression:
    def __init__(
        self,
        tokens: list[Token],
    ):
        self.tokens = tokens

    @classmethod
    def setup_from_expression(
        cls,
        value: ExpressionType,
    ) -> Expression:
        tokens = cls.validate(value)
        return cls(tokens=tokens)

    def __str__(self):
        expression_string = " ".join(str(token) for token in self.tokens)
        expression_string = expression_string.replace(" )", ")")
        expression_string = expression_string.replace("( ", "(")
        return expression_string

    @property
    def variables(self) -> list[str]:
        return [token.value for token in self.tokens if token.tag == TokenTag.reference]

    @classmethod
    def multiply(cls, expression1: Expression, expression2: Expression) -> Expression:
        """Create new expression by multiplying two expressions
        new expression = "(expression1) {*} (expression2)".
        """
        tokens1 = expression1.tokens
        tokens2 = expression2.tokens
        tokens_multiplied = (
            [LEFT_PARENTHESIS_TOKEN]
            + tokens1
            + [RIGHT_PARENTHESIS_TOKEN]
            + [MULTIPLICATION_TOKEN]
            + [LEFT_PARENTHESIS_TOKEN]
            + tokens2
            + [RIGHT_PARENTHESIS_TOKEN]
        )
        return cls(tokens=tokens_multiplied)

    @classmethod
    def validate(cls, expression: Any) -> list[Token]:
        expression = _expression_as_number_if_number(expression_input=expression)

        if not isinstance(expression, str | float | int):
            raise InvalidExpressionError("Expression should be of type str, int or float")

        try:
            return lexer(expression)
        except (KeyError, ValueError) as e:
            raise InvalidExpressionError(message=str(e)) from e

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: Any, handler: GetCoreSchemaHandler) -> CoreSchema:
        def parse_expression(x: Any):
            if isinstance(x, Expression):
                return x

            try:
                return Expression(tokens=cls.validate(x))
            except InvalidExpressionError as e:
                # Raise ValueError for pydantic to pick up
                raise ValueError(str(e)) from e

        from_str_schema = core_schema.chain_schema(
            [
                # core_schema.union_schema(
                #    [core_schema.int_schema(), core_schema.float_schema(), core_schema.str_schema()],
                # ),
                core_schema.no_info_plain_validator_function(parse_expression),
            ]
        )

        def serialize_expression(instance):
            if isinstance(instance, list):
                # TODO[pydantic]: Why is list passed into this? Bug: https://github.com/pydantic/pydantic/issues/6830
                return [serialize_expression(x) for x in instance]
            if isinstance(instance, Expression):
                return str(instance)

            raise ValueError("Wrong type")

        return core_schema.json_or_python_schema(
            json_schema=from_str_schema,
            python_schema=core_schema.union_schema(
                [
                    # check if it's an instance first before doing any further work
                    core_schema.is_instance_schema(Expression),
                    from_str_schema,
                ]
            ),
            serialization=core_schema.plain_serializer_function_ser_schema(serialize_expression),
        )

    @classmethod
    def validator(cls, expression: str | float | int | Expression):
        if isinstance(expression, Expression):
            return expression
        tokens = cls.validate(expression=expression)
        instance = cls(tokens=tokens)
        return instance

    def evaluate(self, variables: dict[str, list[float]], fill_length: int) -> NDArray[np.float64]:
        missing_references = [reference_id for reference_id in self.variables if reference_id not in variables]
        if len(missing_references) != 0:
            msg = f"Unable to evaluate expression. Missing reference(s) {', '.join(missing_references)}"
            logger.error(msg)
            raise InvalidExpressionError(msg)

        tokens = [
            Token(
                tag=TokenTag.numeric,
                value=np.asarray(variables.get(token.value)),
            )
            if token.tag == TokenTag.reference
            else token
            for token in self.tokens
        ]
        try:
            return eval_tokens(tokens=tokens, array_length=fill_length)
        except (KeyError, ValueError) as e:
            raise InvalidExpressionError(message=str(e)) from e

    def __eq__(self, other):
        if not isinstance(other, Expression):
            return NotImplemented
        return self.tokens == other.tokens

    def __repr__(self):
        return f"Expression(tokens={''.join(repr(token) for token in self.tokens)})"

    @classmethod
    def __get_pydantic_json_schema__(
        cls, _core_schema: core_schema.CoreSchema, handler: GetJsonSchemaHandler
    ) -> JsonSchemaValue:
        # TODO: missing pattern, removed when migrating to pydantic v2
        return handler(
            core_schema.union_schema(
                [core_schema.int_schema(), core_schema.float_schema(), core_schema.str_schema()],
            )
        )


def _expression_as_number_if_number(expression_input: ExpressionType) -> ExpressionType:
    """Expressions may be either pure numbers, booleans or strings which define a combination of numbers, operators and
    references as a string. If very small numbers are parsed and represented in scientific notation, the expression
    parsing will wrongfully treat these as expressions with references/operators instead of pure numeric values. Thus,
    all inputs are tested if they can be directly converted to a number, and if so we use the value instead of the
    string representation in further calculations.
    """
    if isinstance(expression_input, str):
        try:
            expression_as_number_if_number = float(expression_input)
        except Exception:
            expression_as_number_if_number = expression_input  # type: ignore[assignment]
    else:
        expression_as_number_if_number = expression_input

    return expression_as_number_if_number
