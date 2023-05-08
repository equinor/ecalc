import pytest
from libecalc.expression.expression_evaluator import (
    TokenTag,
    eval_additions,
    eval_logicals,
    eval_mults,
    eval_parenteses,
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


def test_Parenteses():
    assert eval_parenteses(["(", "5", ")"]) == 5
    assert eval_parenteses(["(", "5", "{+}", "4", ")", "{*}", "2"]) == 18
    assert (
        eval_parenteses(
            ["(", "5", ">", "4", ")", "{+}", "(", "3", ">=", "3", ")"],
        )
        == 2
    )
    assert eval_parenteses(["(", "5", "{+}", "4", ")", "==", "9"]) == 1
    assert (
        eval_parenteses(
            ["(", "(", "5", "{+}", "4", ")", "{*}", "2", "{-}", "3", ")", "{+}", "1"],
        )
        == 16
    )
    assert eval_parenteses(["12", ">=", "7"]) == 1
    assert eval_parenteses(["12", "<", "7"]) == 0
    assert eval_parenteses(["12", "<", "7", "{+}", "6"]) == 1
    assert eval_parenteses(["12", "{-}", "7", "==", "5"]) == 1

    assert eval_parenteses(["12", "{+}", "7"]) == 19
    assert eval_parenteses(["12", "{-}", "7"]) == 5
    assert eval_parenteses(["12", "{*}", "7"]) == 84
    assert eval_parenteses(["10", "{/}", "4"]) == 2.5
