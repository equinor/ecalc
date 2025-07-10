from abc import ABC, abstractmethod

from libecalc.expression import Expression


class TimeSeriesExpressionInterface(ABC):
    """
    Interface for time series expressions.
    """

    @abstractmethod
    def get_expressions(self) -> list[Expression]:
        """
        Returns the expression as a string.
        """
        pass

    @abstractmethod
    def get_evaluated_expressions(self):
        """
        Returns the type of the expression.
        """
        pass
