from libecalc.common.variables import ExpressionEvaluator
from libecalc.presentation.yaml.yaml_types.yaml_variable import YamlVariable


class Variable:
    def __init__(
        self, reference_id: str, name: str, definition: YamlVariable, expression_evaluator: ExpressionEvaluator
    ):
        self._reference_id = reference_id
        self._name = name
        self._definition = definition
        self._expression_evaluator = expression_evaluator
