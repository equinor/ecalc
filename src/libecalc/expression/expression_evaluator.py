from __future__ import annotations

import re
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

"""
Module for expression parsing used in Energy/CO2/emissions calculator

Eval expressions

Variable example: SIM1;OIL_PROD:SC-102

Operators allowed: (with {} to allow + - * / in variable names)
    plus:       {+}
    minus:      {-}
    multiply:   {*}
    division:   {/}
    power:      {^}

Parentheses are supported: ()

Logicals are supported and returns 0 or 1
    Larger than:              >
    Larger than or equal to:  >=
    Smaller than:             <
    Smaller than or equal to: <=
    Equal to:                 ==
    Not equal to:             !=

Example: SIM2;OIL_PROD:SC-102 {*} 2.0 {-} SIM1;OIL_PROD {+} SIM3:OIL_PROD_TOTAL:TMP; {*} (SIM3:OIL_PROD>0)

"""


def lex(expression: str, token_exprs: list[tuple[str, TokenTag | None]]) -> list[Token]:
    pos = 0
    tokens = []

    while pos < len(expression):
        match = None
        for token_expr in token_exprs:
            pattern, tag = token_expr
            regex = re.compile(pattern)
            match = regex.match(expression, pos)
            if match:
                text = match.group(0)
                if tag:
                    token = text  # (text, tag)
                    tokens.append(
                        Token(
                            tag=tag,
                            value=token,
                        )
                    )
                break
        if not match:
            raise KeyError(
                f'Illegal character: "{str(expression[pos])}" in "{expression}". '
                f"Did you forget to put {{}} around operators?"
            )
        else:
            pos = match.end(0)
    return tokens


def lexer(expression: str | int | float) -> list[Token]:
    if isinstance(expression, int | float):
        return [Token(tag=TokenTag.numeric, value=expression)]

    # Arithmetic operators redefined with {} to allow +-*/ et.c. in variable names
    token_exprs = [
        (r"[ \n\t]+", None),
        (r"#[^\n]*", None),
        (r"\:=", TokenTag.operator),
        (r"\(", TokenTag.operator),
        (r"\)", TokenTag.operator),
        (r";", TokenTag.operator),
        (r"\{\+\}", TokenTag.operator),
        (
            r"\{-\}",
            TokenTag.operator,
        ),  # Redef - to {-} to allow - in summary variable names
        (r"\{\*\}", TokenTag.operator),
        (r"\{/\}", TokenTag.operator),
        (r"\{\^\}", TokenTag.operator),
        (r"<=", TokenTag.operator),
        (r"<", TokenTag.operator),
        (r">=", TokenTag.operator),
        (r">", TokenTag.operator),
        (r"==", TokenTag.operator),
        (r"!=", TokenTag.operator),
        (r"[0-9](\.[0-9]+)?e[-+]?[0-9]+", TokenTag.numeric),  # Scientific notation, e.g. 1.23e-05, 3.4e7, 1e+1
        (r"[0-9.]+", TokenTag.numeric),
        (r"[A-Za-z][A-Za-z0-9._;:+*/-]*", TokenTag.reference),
        (r"\$var\.[A-Za-z][A-Za-z0-9_]*", TokenTag.reference),
    ]

    return lex(expression, token_exprs)


class TokenTag(Enum):
    reference = "ID"
    operator = "RESERVED"
    numeric = "NUMBER"


class Token(BaseModel):
    tag: TokenTag
    value: float | int | str = Field(union_mode="left_to_right")

    def __str__(self):
        return str(self.value)

    model_config = ConfigDict(arbitrary_types_allowed=True)
