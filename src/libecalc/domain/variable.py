from libecalc.common.utils.rates import Rates
from libecalc.common.variables import ExpressionEvaluator
from libecalc.domain.interfaces.variable_interface import VariableInterface
from libecalc.domain.regularity import Regularity
from libecalc.dto.utils.validators import convert_expression
from libecalc.expression.expression import ExpressionType


class Variable(VariableInterface):
    def __init__(
        self,
        name: str,
        expression: ExpressionType,
        expression_evaluator: ExpressionEvaluator,
        regularity: Regularity,
        is_rate: bool = True,
    ):
        self._name = name
        self._expression = convert_expression(expression)
        self._expression_evaluator = expression_evaluator
        self._regularity = regularity
        self._is_rate = is_rate

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_rate(self) -> bool:
        # TODO: Make this more robust, if the name is "rate", we assume it is a rate variable
        # TODO: This flag should be used instead of checking the name
        return self._is_rate

    def get_values(self) -> list[float]:
        if self._expression is None:
            return []

        variable_values = self._expression_evaluator.evaluate(self._expression)

        # If some of these are rates, we need to calculate stream day rate for use
        # Also take a copy of the calendar day rate and stream day rate for input to result object

        if self.name.lower() == "rate":
            variable_values = Rates.to_stream_day(
                calendar_day_rates=variable_values,
                regularity=self._regularity.get_values,
            )
        return variable_values.tolist()
