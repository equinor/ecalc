import numpy as np
import pytest
from libecalc.expression.expression_evaluator import (
    TokenTag,
    count_parentheses,
    eval_additions,
    eval_logicals,
    eval_mults,
    eval_parentheses,
    eval_powers,
    lex,
    lexer,
)


def test_lex():
    token_exprs = [
        (r"[ \n\t]+", None),
        (r"#[^\n]*", None),
        (r"\(", TokenTag.operator),
        (r"\)", TokenTag.operator),
        (r"\{\+\}", TokenTag.operator),
        (r"\{-\}", TokenTag.operator),
        (r"\{\*\}", TokenTag.operator),
        (r"\{/\}", TokenTag.operator),
        (r"\{\^\}", TokenTag.operator),
        (r"<=", TokenTag.operator),
        (r"<", TokenTag.operator),
        (r">=", TokenTag.operator),
        (r">", TokenTag.operator),
        (r"==", TokenTag.operator),
        (r"!=", TokenTag.operator),
        (r"[0-9.]+", TokenTag.numeric),
        (r"[A-Za-z][A-Za-z0-9_;:+*/-]*", TokenTag.reference),
    ]
    expression = " 2 {+} ( (2>=1) {+} 1 ) {*} 50 {-} 3 {/} (2) "
    output = lex(expression, token_exprs)
    compare = [
        2.0,
        "{+}",
        "(",
        "(",
        2.0,
        ">=",
        1.0,
        ")",
        "{+}",
        1.0,
        ")",
        "{*}",
        50.0,
        "{-}",
        3.0,
        "{/}",
        "(",
        2.0,
        ")",
    ]
    token_values = [token.value for token in output]
    assert token_values == compare


def test_lexer():
    expression = " 2 {+} ( (2>=1) {+} 1 ) {*} 50 {-} 3 {/} (2) "
    tokens = lexer(expression)
    compare = [
        2.0,
        "{+}",
        "(",
        "(",
        2.0,
        ">=",
        1.0,
        ")",
        "{+}",
        1.0,
        ")",
        "{*}",
        50.0,
        "{-}",
        3.0,
        "{/}",
        "(",
        2.0,
        ")",
    ]

    token_values = [token.value for token in tokens]
    assert token_values == compare

    expression = " 2 {+} 2 {^} 2 {*} (3{+}1)"

    tokens = lexer(expression)
    compare = [2.0, "{+}", 2.0, "{^}", 2.0, "{*}", "(", 3.0, "{+}", 1.0, ")"]
    token_values = [token.value for token in tokens]
    assert token_values == compare


# disable formatting to prevent black from removing '+' from numbers with scientific notation
# fmt: off
scientific_expressions = [
    ("1.1e1", [1.1e1], [TokenTag.numeric]),
    ("1.1e111", [1.1e111], [TokenTag.numeric]),
    ("1.1e+1", [1.1e+1], [TokenTag.numeric]),
    ("1.1e-1", [1.1e-1], [TokenTag.numeric]),
    ("1.1e-000001", [1.1e-000001], [TokenTag.numeric]),
    ("1.1e+111", [1.1e+111], [TokenTag.numeric]),
    ("1.1e-111", [1.1e-111], [TokenTag.numeric]),
    ("1.111e1", [1.111e1], [TokenTag.numeric]),
    ("1.111e+1", [1.111e+1], [TokenTag.numeric]),
    ("1.111e-1", [1.111e-1], [TokenTag.numeric]),
    ("1.111e-111", [1.111e-111], [TokenTag.numeric]),
    ("1e1", [1e1], [TokenTag.numeric]),
    ("1e+1", [1e+1], [TokenTag.numeric]),
    ("1e-1", [1e-1], [TokenTag.numeric]),
    ("1e-111", [1e-111], [TokenTag.numeric]),
    (
        "2.4e6 {/} 100 {*} 1.35e-05{+}  2e14 {-} 6.543e+11 {^} VARIABLE;VAL1",
        [2.4e6, "{/}", 100.0, "{*}", 1.35e-05, "{+}", 2e14, "{-}", 6.543e+11, "{^}", "VARIABLE;VAL1"],
        [
            TokenTag.numeric,
            TokenTag.operator,
            TokenTag.numeric,
            TokenTag.operator,
            TokenTag.numeric,
            TokenTag.operator,
            TokenTag.numeric,
            TokenTag.operator,
            TokenTag.numeric,
            TokenTag.operator,
            TokenTag.reference,
        ],
    ),
]
# fmt: on


@pytest.mark.parametrize(
    "expression, expected, expected_token_tags",
    scientific_expressions,
)
def test_lexer_scientific(expression, expected, expected_token_tags):
    tokens = lexer(expression)
    assert [token.value for token in tokens] == expected
    assert [token.tag for token in tokens] == expected_token_tags


def test_Powers(caplog):
    caplog.set_level("CRITICAL")
    with pytest.raises(Exception):
        tokens = ["2", "{^}", "2", "{^}", "2"]
        eval_powers(tokens)
    assert eval_powers(["3", "{^}", "3"]) == 27.0


def test_Mults():
    assert eval_mults(["12", "{*}", "7"]) == 84
    assert eval_mults(["10", "{/}", "4"]) == 2.5
    assert eval_mults(["10", "{*}", "2", "{^}", "2"]) == 40.0


def test_Additions():
    assert eval_additions(["12", "{+}", "7"]) == 19
    assert eval_additions(["12", "{-}", "7"]) == 5
    assert eval_additions(["12", "{*}", "7"]) == 84
    assert eval_additions(["10", "{/}", "4"]) == 2.5
    assert eval_additions(["2", "{^}", "4"]) == 16.0
    assert eval_additions(["2", "{+}", "2", "{^}", "4", "{*}", "2"]) == 34.0


def test_logicals():
    assert eval_logicals(["12", ">=", "7"]) == 1
    assert eval_logicals(["12", "<", "7"]) == 0
    assert eval_logicals(["12", "<", "7", "{+}", "6"]) == 1
    assert eval_logicals(["12", "{-}", "7", "==", "5"]) == 1
    assert eval_logicals(["12", "{+}", "7"]) == 19
    assert eval_logicals(["12", "{-}", "7"]) == 5
    assert eval_logicals(["12", "{*}", "7"]) == 84
    assert eval_logicals(["10", "{/}", "4"]) == 2.5


def test_eval_parentheses():
    assert eval_parentheses(["(", "5", ")"]) == 5
    assert eval_parentheses(["(", "5", "{+}", "4", ")", "{*}", "2"]) == 18
    assert (
        eval_parentheses(
            ["(", "5", ">", "4", ")", "{+}", "(", "3", ">=", "3", ")"],
        )
        == 2
    )
    assert eval_parentheses(["(", "5", "{+}", "4", ")", "==", "9"]) == 1
    assert (
        eval_parentheses(
            ["(", "(", "5", "{+}", "4", ")", "{*}", "2", "{-}", "3", ")", "{+}", "1"],
        )
        == 16
    )
    assert eval_parentheses(["12", ">=", "7"]) == 1
    assert eval_parentheses(["12", "<", "7"]) == 0
    assert eval_parentheses(["12", "<", "7", "{+}", "6"]) == 1
    assert eval_parentheses(["12", "{-}", "7", "==", "5"]) == 1

    assert eval_parentheses(["12", "{+}", "7"]) == 19
    assert eval_parentheses(["12", "{-}", "7"]) == 5
    assert eval_parentheses(["12", "{*}", "7"]) == 84
    assert eval_parentheses(["10", "{/}", "4"]) == 2.5


def test_count_parentheses():
    assert count_parentheses(
        ["(", "5", ">", "4", ")", "{+}", "(", "3", ">=", "3", ")"],
    ) == (2, 2)
    assert count_parentheses(
        ["(", np.asarray([1, 2, 3]), ">", "4", ")", "{+}", "(", "3", ">=", "3", ")"],
    ) == (2, 2)
    assert count_parentheses(
        [["("], np.asarray([1, 2, 3]), ">", "4", ")", "{+}", "(", "3", ">=", "3", ")"],
    ) == (1, 2)
    assert count_parentheses([1, 2, 3]) == (0, 0)
