from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal, assert_never

import numpy as np
from numpy._typing import NDArray

from libecalc.expression.expression_evaluator import OPERATORS, Operators, Token, TokenTag

operand_types = (TokenTag.numeric, TokenTag.reference)

precedence: dict[str, tuple[int, Literal["RIGHT"] | Literal["LEFT"]]] = {
    Operators.power.value: (24, "RIGHT"),
    Operators.multiply.value: (23, "LEFT"),
    Operators.divide.value: (23, "LEFT"),
    Operators.add.value: (22, "LEFT"),
    Operators.subtract.value: (22, "LEFT"),
    Operators.equal.value: (16, "LEFT"),
    Operators.not_equal.value: (15, "LEFT"),
    # Operators.less_than.value: (14, "LEFT"),
    Operators.larger_than.value: (13, "LEFT"),
    Operators.less_than_or_equal.value: (12, "LEFT"),
    Operators.larger_than_or_equal.value: (11, "LEFT"),
}


def get_precedence(token: Token) -> int:
    assert isinstance(token.value, str)
    return precedence[token.value][0]


def get_associativity(token: Token) -> Literal["LEFT"] | Literal["RIGHT"]:
    assert isinstance(token.value, str)
    return precedence[token.value][1]


def get_postfix(infix_tokens: list[Token]) -> list[Token]:
    """
    Convert infix tokens to postfix tokens.

    https://en.wikipedia.org/wiki/Shunting_yard_algorithm

    Args:
        infix_tokens:

    Returns: tokens in postfix

    """
    postfix_tokens = []
    stack: list[Token] = []
    for token in infix_tokens:
        if token.tag in operand_types:
            postfix_tokens.append(token)
        elif token.tag == TokenTag.operator and token.value not in ["(", ")"]:
            while True:
                if len(stack) == 0:
                    break

                o2 = stack[-1]
                if o2.value == "(":
                    break
                o2_precedence = get_precedence(o2)
                o1_precedence = get_precedence(token)
                if o2_precedence > o1_precedence or (
                    o1_precedence == o2_precedence and get_associativity(token) == "LEFT"
                ):
                    postfix_tokens.append(stack.pop())
                else:
                    break
            stack.append(token)
        elif token.value == "(":
            stack.append(token)

        elif token.value == ")":
            while True:
                if len(stack) == 0:
                    raise ValueError("Number of left and right parentheses do not match")

                o2 = stack[-1]

                if o2.value != "(":
                    postfix_tokens.append(stack.pop())
                else:
                    break

            assert stack[-1].value == "("
            stack.pop()

    while len(stack) > 0:
        if stack[-1].value == "(":
            raise ValueError("Number of left and right parentheses do not match")

        postfix_tokens.append(stack.pop())

    return postfix_tokens


@dataclass(repr=True)
class Node:
    token: Token
    left: Node | None = None
    right: Node | None = None

    def evaluate(self, variables: dict[str, Any], fill_length: int) -> NDArray[np.float64]:
        if self.token.tag == TokenTag.operator:
            assert isinstance(self.token.value, str)
            return np.nan_to_num(
                OPERATORS[self.token.value](
                    self.left.evaluate(variables, fill_length), self.right.evaluate(variables, fill_length)
                ).astype(float)
            )  # astype(float) to convert bools to float -> make sure True + True is 2
        elif self.token.tag == TokenTag.numeric:
            assert isinstance(self.token.value, float | int)
            return np.asarray([self.token.value] * fill_length)
        elif self.token.tag == TokenTag.reference:
            assert isinstance(self.token.value, str)
            return np.asarray(variables[self.token.value])
        else:
            return assert_never(self.token.tag)


# TODO: Look into error handling, unknown operator, unknown variable (list variables), parenthesis (handled)
#       Clean up code, collect operator value, precedence, associativity and calculation into one place.
#       Also check parsing in lexer in terms of token value type, float, int, str, token value as operator?


def get_tree(postfix_tokens: list[Token]) -> Node:
    stack: list[Node] = []
    for token in postfix_tokens:
        if token.tag == TokenTag.operator:
            try:
                right = stack.pop()
                left = stack.pop()
            except IndexError as e:
                raise ValueError("Missing operand in expression") from e
            assert right is not None and left is not None
            new_node = Node(token, left, right)
            stack.append(new_node)
        else:
            stack.append(Node(token=token))

    return stack.pop()
