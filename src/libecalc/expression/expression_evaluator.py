from __future__ import annotations

import operator as op
import re
import warnings
from enum import Enum
from numbers import Number

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict, Field

from libecalc.common.logger import logger
from libecalc.core.utils.array_type import PydanticNDArray

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


def eval_tokens(tokens: list[Token], array_length: int) -> NDArray[np.float64]:
    token_values = [token.value for token in tokens]
    check_tokens(token_values)

    evaluated_values = np.nan_to_num(
        x=eval_parentheses(
            tokens=token_values,
        )  # type: ignore[arg-type]
    )

    if isinstance(evaluated_values, Number | int | float):
        evaluated_values = np.full(fill_value=evaluated_values, shape=array_length)
    return evaluated_values


def eval_parentheses(
    tokens: list[float | int | bool | NDArray[np.float64] | str],
    original_expression: str | None = None,
) -> NDArray[np.float64] | Number:
    """Evaluate expressions within parentheses"""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        number_of_left_parentheses, number_of_right_parentheses = count_parentheses(tokens=tokens)
        while number_of_left_parentheses or number_of_right_parentheses:
            if number_of_left_parentheses != number_of_right_parentheses:
                error_message = "Number of left and right parentheses do not match"
                if original_expression is not None:
                    error_message += f" for expression '{original_expression}'"
                raise ValueError(error_message)

            ind = 0
            while ind < len(tokens) and str(tokens[ind]) != ")":
                ind += 1
            subend = ind
            while ind >= 0 and str(tokens[ind]) != "(":
                ind -= 1
            substart = ind

            tokens_to_evaluate = tokens[substart + 1 : subend]

            try:
                tokens_evaluated = eval_parentheses(
                    tokens_to_evaluate,
                    original_expression=original_expression,
                )
            except Exception as e:
                logger.exception(e)
                errorstr = ""
                if tokens_to_evaluate:
                    for token in tokens_to_evaluate:
                        if isinstance(token, np.ndarray):
                            errorstr += "array(len=" + str(len(token)) + ") "
                        else:
                            errorstr += str(token) + " "
                raise ValueError(
                    "expression evaluator" + ": I have trouble calculating the expression: " + errorstr
                ) from e

            tokens = tokens[:substart] + [tokens_evaluated] + tokens[subend + 1 :]
            number_of_left_parentheses, number_of_right_parentheses = count_parentheses(tokens=tokens)

    return eval_logicals(tokens)


def count_parentheses(tokens: list[float | int | bool | NDArray[np.float64] | str]) -> tuple[int, int]:
    """Count the number of left "(" and right ")" parentheses in a list of tokens"""
    strings_in_tokens = [element for element in tokens if isinstance(element, str)]
    return strings_in_tokens.count(Operators.left_parenthesis.value), strings_in_tokens.count(
        Operators.right_parenthesis.value
    )


def eval_logicals(tokens):
    """Evaluate logical operators in expression"""
    logical_ops = [">", "<", ">=", "<=", "==", "!="]
    ind = 0
    while ind < len(tokens):
        if str(tokens[ind]) in logical_ops:
            divind = ind
            left_tokens = tokens[0:divind]
            right_tokens = tokens[divind + 1 :]
            # Check that there are not more than one logical operator in tokens
            for right_tok in right_tokens:
                if str(right_tok)[0] in logical_ops or str(right_tok)[:2] in logical_ops:
                    raise KeyError("Not more than one logical operator within each parenthesis set")
            return np.array(
                OPERATORS[tokens[divind]](
                    eval_additions(left_tokens),
                    eval_additions(right_tokens),
                ),
                dtype=float,
            )
        ind += 1
    return eval_additions(tokens)


def eval_additions(tokens):
    """Evaluate additions and subtractions in expression"""
    add_ops = ["{+}", "{-}"]
    values = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if any(ops in token if hasattr(token, "__iter__") else ops == token for token in tokens for ops in add_ops):
            ind = 0
            seqstart = 0
            signNext = 1.0
            while ind < len(tokens):
                if str(tokens[ind]) in add_ops:
                    values.append(signNext * eval_mults(tokens[seqstart:ind]))
                    signNext = 1.0 if tokens[ind] == "{+}" else -1.0
                    seqstart = ind + 1
                ind += 1
            if tokens[seqstart - 1] == "{+}":
                values.append(eval_mults(tokens[seqstart:ind]))
            else:
                values.append(-1.0 * eval_mults(tokens[seqstart:ind]))

        else:
            values.append(eval_mults(tokens))
    return sum(values)


def eval_mults(tokens):
    """Evaluate multiplications in expression"""
    mult_ops = ["{*}", "{/}"]
    values = []

    # We may sometimes divide by zero in large vectors, but as these values might get removed
    # by conditions later, we allow this and ignore related warnings
    current_numpy_error = np.geterr()
    np.seterr(divide="ignore", invalid="ignore")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if any(ops in token if hasattr(token, "__iter__") else ops == token for token in tokens for ops in mult_ops):
            ind = 0
            seqstart = 0
            opnext = "mult"
            while ind < len(tokens):
                if str(tokens[ind]) in mult_ops:
                    if opnext == "mult":
                        values.append(eval_powers(tokens[seqstart:ind]))
                    else:
                        denominator = eval_powers(tokens[seqstart:ind])
                        # By default, this throws a warning when denomonator contains 0
                        # Want to allow division by 0 here, as these values may be ruled out later anyway
                        # by conditions
                        mult = np.divide(1.0, denominator)
                        values.append(mult)
                    opnext = "mult" if tokens[ind] == "{*}" else "div"
                    seqstart = ind + 1
                ind += 1
            if tokens[seqstart - 1] == "{*}":
                values.append(eval_powers(tokens[seqstart:ind]))
            else:
                denominator = eval_powers(tokens[seqstart:ind])
                mult = np.divide(1.0, denominator)
                values.append(mult)
        else:
            tmp = eval_powers(tokens)
            if tmp is not None:
                values.append(eval_powers(tokens))
        value = 1.0
        for factor in values:
            value = value * factor
        np.seterr(**current_numpy_error)
    return np.nan_to_num(value)


def eval_powers(tokens):
    """Evaluate exponential calculations in expression"""
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        if any("{^}" in token if hasattr(token, "__iter__") else "{^}" == token for token in tokens):
            if len(tokens) != 3:
                raise ValueError("Number of tokens needs to be 3 for evalPowers, quotient, {^} and exponent")
            quotient = eval_value([tokens[0]])
            exponent = eval_value([tokens[2]])
            value = np.power(quotient, exponent)
        else:
            value = eval_value(tokens)

    return np.nan_to_num(value)


def eval_value(tokens):
    numpattern = r"[0-9.]+"
    regexnumber = re.compile(numpattern)

    if type(tokens) is NDArray[np.float64]:
        var = tokens[0]
    elif len(tokens) < 1:
        raise ValueError(f"expression_evaluator: I can not evaluate {tokens}")
    elif len(tokens) > 2:
        outtext = "Wrong format of variable "
        for ind in range(len(tokens)):
            outtext += " " + str(tokens[ind])
        raise Exception(outtext)
    elif len(tokens) == 2:
        raise ValueError("Should not enter here - no time series in expression evaluator")
    elif isinstance(tokens[0], int | float):
        return float(tokens[0])
    else:
        pos = 0
        match = regexnumber.match(str(tokens[0]), pos)
        if match:  # This is a number
            return float(match.group(0))
        elif type(tokens[0]) is not np.ndarray:
            tmp = tokens[0].split(";")
            if len(tmp) != 2:
                raise KeyError(
                    'Not correct format of reservoir variable "'
                    + tokens[0]
                    + '", did you forget to specify reservoir case (e.g. "SIM1;'
                    + tokens[0]
                    + '")?'
                )
            raise ValueError("Should not enter here - no time series in expression evaluator")
        else:
            var = tokens[0]
    var = np.nan_to_num(var)
    return var


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

    number_of_left_parentheses = expression.count(Operators.left_parenthesis.value)
    number_of_right_parentheses = expression.count(Operators.right_parenthesis.value)
    if number_of_left_parentheses != number_of_right_parentheses:
        raise ValueError(f"Number of left and right parentheses do not match for expression '{expression}'")

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
        (r"and", TokenTag.operator),
        (r"or", TokenTag.operator),
        (r"not", TokenTag.operator),
        (r"if", TokenTag.operator),
        (r"then", TokenTag.operator),
        (r"else", TokenTag.operator),
        (r"while", TokenTag.operator),
        (r"do", TokenTag.operator),
        (r"end", TokenTag.operator),
        (r"[0-9](\.[0-9]+)?e[-+]?[0-9]+", TokenTag.numeric),  # Scientific notation, e.g. 1.23e-05, 3.4e7, 1e+1
        (r"[0-9.]+", TokenTag.numeric),
        (r"[A-Za-z][A-Za-z0-9._;:+*/-]*", TokenTag.reference),
        (r"\$var\.[A-Za-z][A-Za-z0-9_]*", TokenTag.reference),
    ]

    return lex(expression, token_exprs)


OPERATORS = {
    "{+}": op.add,
    "{-}": op.sub,
    "{/}": op.truediv,
    "{*}": op.mul,
    "{^}": op.pow,
    ">": op.gt,
    ">=": op.ge,
    "<": op.lt,
    "<=": op.le,
    "==": op.eq,
    "ne": op.ne,
}


# Check that two operators are not coming after each other, e.g. {+} {-} or {+} > et.c.
def check_tokens(tokens):
    tokens_dummy = ["ref" if isinstance(token, np.ndarray) else str(token) for token in tokens]
    var = " ".join(tokens_dummy)
    first_token, last_token = tokens[0], tokens[-1]
    if str(first_token) in list(OPERATORS.keys()):
        raise ValueError(f"Expression ({var}) can not start with an operator")
    if str(last_token) in list(OPERATORS.keys()):
        raise ValueError(f"Expression ({var}) can not end with an operator")
    for idx, token in enumerate(tokens):
        prev_token = tokens[idx - 1]
        if str(prev_token) in list(OPERATORS.keys()) and str(token) in list(OPERATORS.keys()):
            raise ValueError(f"Expression ({var}) can not have two operators after each other")


class TokenTag(Enum):
    reference = "ID"
    operator = "RESERVED"
    numeric = "NUMBER"


class Operators(Enum):
    add = "{+}"
    subtract = "{-}"
    divide = "{/}"
    multiply = "{*}"
    power = "{^}"
    left_parenthesis = "("
    right_parenthesis = ")"
    larger_than = ">"
    larger_than_or_equal = ">="
    less_than = "<"
    less_than_or_equal = "<="
    equal = "=="
    not_equal = "ne"


class Token(BaseModel):
    tag: TokenTag
    value: float | int | bool | PydanticNDArray | str = Field(union_mode="left_to_right")

    def __str__(self):
        return str(self.value)

    model_config = ConfigDict(arbitrary_types_allowed=True)
