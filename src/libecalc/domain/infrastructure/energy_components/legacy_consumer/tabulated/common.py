from __future__ import annotations

from libecalc.expression import Expression


class VariableExpression:
    def __init__(self, name: str, expression: Expression):
        self.name = name
        self.expression = expression


class Variable:
    def __init__(self, name: str, values: list[float]):
        self.name = name
        self.values = values
