from abc import ABC, abstractmethod

from libecalc.expression import Expression


class TimeSeriesExpressionInterface(ABC):
    """
    Interface for time series expressions.
    """

    @abstractmethod
    def get_expressions(self) -> list[Expression]:
        """
        Returns the list of converted expressions.
        """
        pass

    @abstractmethod
    def get_evaluated_expressions(self):
        """
        Evaluates all expressions and returns their results as a NumPy array.
        """
        pass
