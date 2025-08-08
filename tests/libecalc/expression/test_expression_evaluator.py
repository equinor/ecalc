import pytest

from libecalc.expression.expression_evaluator import (
    TokenTag,
    lexer,
)


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
