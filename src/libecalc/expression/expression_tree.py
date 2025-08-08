from __future__ import annotations

import operator as op
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal, NamedTuple, assert_never

import numpy as np
from numpy.typing import NDArray

from libecalc.expression.expression_evaluator import Token, TokenTag

operand_types = (TokenTag.numeric, TokenTag.reference)


def get_operator(token: Token) -> Operator:
    assert isinstance(token.value, str)
    try:
        return OPERATORS[token.value]
    except KeyError as e:
        raise ValueError(f"Operator '{token.value}' is not supported") from e


def get_precedence(token: Token) -> int:
    return get_operator(token).precedence


def get_associativity(token: Token) -> Literal["LEFT"] | Literal["RIGHT"]:
    return get_operator(token).associativity


def get_operation(token: Token) -> Callable:
    return get_operator(token).function


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
                get_operation(self.token)(
                    self.left.evaluate(variables, fill_length), self.right.evaluate(variables, fill_length)
                ).astype(float)
            )  # astype(float) to convert bools to float -> make sure True + True is 2
        elif self.token.tag == TokenTag.numeric:
            assert isinstance(self.token.value, float | int)
            return np.nan_to_num(np.asarray([self.token.value] * fill_length)).astype(float)
        elif self.token.tag == TokenTag.reference:
            assert isinstance(self.token.value, str)
            assert self.token.value in variables
            return np.asarray(variables[self.token.value]).astype(float)
        else:
            return assert_never(self.token.tag)


def get_tree(postfix_tokens: list[Token]) -> Node:
    stack: list[Node] = []
    for token in postfix_tokens:
        if token.tag == TokenTag.operator:
            try:
                right = stack.pop()
            except IndexError as e:
                raise ValueError(f"Missing left operand for operator '{token.value}'") from e
            try:
                left = stack.pop()
            except IndexError as e:
                raise ValueError(f"Missing right operand for operator '{token.value}'") from e
            new_node = Node(token, left, right)
            stack.append(new_node)
        else:
            stack.append(Node(token=token))

    return stack.pop()


class Operator(NamedTuple):
    value: str
    function: Callable
    precedence: int
    associativity: Literal["RIGHT"] | Literal["LEFT"]


OPERATORS = {
    "{^}": Operator(value="{^}", function=op.pow, precedence=24, associativity="RIGHT"),
    "{*}": Operator(value="{*}", function=op.mul, precedence=23, associativity="LEFT"),
    "{/}": Operator(value="{/}", function=op.truediv, precedence=23, associativity="LEFT"),
    "{+}": Operator(value="{+}", function=op.add, precedence=22, associativity="LEFT"),
    "{-}": Operator(value="{-}", function=op.sub, precedence=22, associativity="LEFT"),
    "==": Operator(value="==", function=op.eq, precedence=16, associativity="LEFT"),
    "!=": Operator(value="ne", function=op.ne, precedence=15, associativity="LEFT"),
    "<": Operator(value="ne", function=op.lt, precedence=14, associativity="LEFT"),
    ">": Operator(value="{>}", function=op.gt, precedence=13, associativity="LEFT"),
    "<=": Operator(value="{<=}", function=op.le, precedence=12, associativity="LEFT"),
    ">=": Operator(value="{>=}", function=op.ge, precedence=11, associativity="LEFT"),
}
