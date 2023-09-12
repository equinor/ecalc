from __future__ import annotations

from typing import Dict, List, Union

import numpy as np
from libecalc.common.logger import logger
from libecalc.expression.expression_evaluator import (
    Operators,
    Token,
    TokenTag,
    eval_tokens,
    lexer,
)
from numpy.typing import NDArray

LEFT_PARENTHESIS_TOKEN = Token(tag=TokenTag.operator, value=Operators.left_parenthesis.value)
RIGHT_PARENTHESIS_TOKEN = Token(tag=TokenTag.operator, value=Operators.right_parenthesis.value)
MULTIPLICATION_TOKEN = Token(tag=TokenTag.operator, value=Operators.multiply.value)

ExpressionType = Union[str, float, int]


class Expression:
    def __init__(
        self,
        tokens: List[Token],
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
    def variables(self) -> List[str]:
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
    def validate(cls, expression: ExpressionType) -> List[Token]:
        expression = _expression_as_number_if_number(expression_input=expression)

        if not isinstance(expression, (str, float, int)):
            raise ValueError("Expression should be of type str, int or float")
        return lexer(expression)

    @classmethod
    def validator(cls, expression: Union[str, float, int, Expression]):
        if isinstance(expression, Expression):
            return expression
        tokens = cls.validate(expression=expression)
        return cls(tokens=tokens)

    def evaluate(self, variables: Dict[str, List[float]], fill_length: int) -> NDArray[np.float64]:
        missing_references = [reference_id for reference_id in self.variables if reference_id not in variables]
        if len(missing_references) != 0:
            msg = f"Unable to evaluate expression. Missing reference(s) {', '.join(missing_references)}"
            logger.error(msg)
            raise ValueError(msg)

        tokens = [
            Token(
                tag=TokenTag.numeric,
                value=np.asarray(variables.get(token.value)),
            )
            if token.tag == TokenTag.reference
            else token
            for token in self.tokens
        ]

        return eval_tokens(tokens=tokens, array_length=fill_length)

    def __eq__(self, other):
        if not isinstance(other, Expression):
            return NotImplemented
        return self.tokens == other.tokens

    def __repr__(self):
        return f"Expression(tokens={''.join(repr(token) for token in self.tokens)})"

    @classmethod
    def __modify_schema__(cls, field_schema):
        field_schema.update(
            title="Expression",
            anyOf=[
                {"type": "integer"},
                {"type": "number"},
                {
                    "type": "string",
                    "pattern": r"^[\w * ^ . : ; () {} = > < + \- /]+$",
                },
            ],
            examples=["SIM1;OIL_PROD {+} 1000", 5],
        )

    @classmethod
    def __get_validators__(cls):
        yield cls.validator


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
