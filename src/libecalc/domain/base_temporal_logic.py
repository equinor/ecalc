from abc import ABC, abstractmethod
from datetime import datetime

from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Period, define_time_model_for_period
from libecalc.common.variables import ExpressionEvaluator
from libecalc.dto.utils.validators import validate_temporal_model
from libecalc.expression.expression import Expression, ExpressionType


class BaseTemporalLogic(ABC):
    """
    Base class for temporal models with shared functionality.

    This class provides a foundation for temporal logic models, handling the
    normalization and evaluation of expressions over a specified time period.
    Subclasses must implement specific methods for returning time series data
    and defining default expression values.

    Attributes:
        - name (str): The name of the temporal model.
        - expression_evaluator (ExpressionEvaluator): Evaluates expressions for the temporal model.
        - target_period (Period): The time period over which the model is evaluated.
        - expression (ExpressionType | dict[datetime, ExpressionType] | None):
            The input expression or dictionary of expressions defining the model.
        - data (dict[Period, Expression]): The normalized expression data mapped to time periods.
        - _values (list[float]): The evaluated values for the temporal model.

    Methods:
        - values() -> list[float]:
            Returns the evaluated values for the temporal model.
        - time_series():
            Abstract method to return time series data for the model.
        - default_expression_value() -> float:
            Abstract method to return the default expression value for the model.
    """

    def __init__(
        self,
        name: str,
        expression_evaluator: ExpressionEvaluator,
        target_period: Period,
        expression: ExpressionType | dict[datetime, ExpressionType] | None = None,
    ):
        self.name = name
        self.expression_evaluator = expression_evaluator
        self.target_period = target_period
        self.expression = expression

        # Normalize expression to a dict[Period, Expression]
        self.data: dict[Period, Expression] = self._normalize_expression()

        validate_temporal_model(self.data)
        self._values = self._evaluate()

    @property
    def values(self) -> list[float]:
        """
        Returns the evaluated values for the temporal model.
        """
        return self._values

    def _evaluate(self) -> list[float]:
        """
        Evaluates the temporal model over the defined time periods.
        """
        return self.expression_evaluator.evaluate(expression=TemporalModel(self.data)).tolist()

    def _normalize_expression(self) -> dict[Period, Expression]:
        """
        Normalizes the input expression into a dict[Period, Expression].
        """
        if isinstance(self.expression, dict):
            return {
                period: Expression.setup_from_expression(value)
                for period, value in define_time_model_for_period(self.expression, self.target_period).items()
            }
        elif self.expression is not None:
            return define_time_model_for_period(
                Expression.setup_from_expression(self.expression), target_period=self.target_period
            )
        return define_time_model_for_period(
            Expression.setup_from_expression(self.default_expression_value()), target_period=self.target_period
        )

    @abstractmethod
    def time_series(self):
        """
        Abstract method to be implemented by subclasses for returning time series data.
        """
        pass

    @abstractmethod
    def default_expression_value(self) -> float:
        """
        Returns the default expression value for the subclass.
        """
        pass
