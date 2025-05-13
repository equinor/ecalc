from datetime import datetime

from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period, define_time_model_for_period
from libecalc.common.variables import ExpressionEvaluator
from libecalc.expression.expression import Expression, ExpressionType


class TemporalExpression:
    """
    A utility class for handling temporal expressions mapped to specific periods.

    Attributes:
        - model (TemporalModel[Expression]): The temporal model containing expressions mapped to periods.
        - evaluator (ExpressionEvaluator): The evaluator used for evaluating expressions.
    """

    def __init__(
        self,
        expression: ExpressionType | dict[datetime, ExpressionType],
        target_period: Period,
        expression_evaluator: ExpressionEvaluator,
    ):
        self.target_period = target_period
        self.expression = expression
        self.expression_evaluator = expression_evaluator

        # Normalize expression into a TemporalModel
        self.model = self._normalize_expression()

    def _normalize_expression(self) -> TemporalModel[Expression]:
        """
        Normalizes the input expression into a TemporalModel[Expression].
        """
        if isinstance(self.expression, dict):
            data = {
                period: Expression.setup_from_expression(value)
                for period, value in define_time_model_for_period(self.expression, self.target_period).items()
            }
        elif self.expression is not None:
            data = define_time_model_for_period(
                Expression.setup_from_expression(self.expression), target_period=self.target_period
            )
        else:
            raise ValueError("Expression must be provided for TemporalExpression.")

        return TemporalModel(data)

    def evaluate(self) -> list[float]:
        """
        Evaluates the expressions for all periods using the provided evaluator.
        """
        return self.expression_evaluator.evaluate(self.model).tolist()
