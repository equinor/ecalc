from datetime import datetime
from typing import Self

from libecalc.common.time_utils import Period
from libecalc.common.units import Unit
from libecalc.common.utils.rates import TimeSeriesFloat
from libecalc.common.variables import ExpressionEvaluator
from libecalc.expression.expression import ExpressionType, InvalidExpressionError
from libecalc.expression.temporal_expression import TemporalExpression


class InvalidRegularity(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class Regularity:
    """
    Represents the regularity for an installation.

    This class models the regularity values over a specified time period,
    including validation to ensure they are valid fractions between 0 and 1.
    """

    def __init__(
        self,
        expression_evaluator: ExpressionEvaluator,
        target_period: Period,
        expression_input: ExpressionType | dict[Period, ExpressionType] | dict[datetime, ExpressionType] | None = None,
    ):
        self.target_period = target_period
        self.expression_evaluator = expression_evaluator
        try:
            self.temporal_expression = TemporalExpression(
                expression=expression_input or self.default_expression_value(),
                target_period=target_period,
                expression_evaluator=expression_evaluator,
            )
        except (ValueError, InvalidExpressionError) as e:
            raise InvalidRegularity(str(e)) from e
        self.validate()

    @property
    def values(self) -> list[float]:
        return self.time_series.values

    @property
    def time_series(self) -> TimeSeriesFloat:
        """
        Returns the evaluated regularity values as a time series.
        """
        return TimeSeriesFloat(
            periods=self.expression_evaluator.get_periods(),
            values=self.temporal_expression.evaluate(),
            unit=Unit.NONE,
        )

    @staticmethod
    def default_expression_value() -> float:
        """
        Returns the default expression value for Regularity.
        """
        return 1

    def validate(self):
        """
        Validates the evaluated regularity values for the installation.

        Ensures that all values in the `evaluated_regularity` time series are fractions
        between 0 and 1. If any value falls outside this range, a `ComponentValidationException`
        is raised with details about the invalid value and its location.

        Raises:
            ComponentValidationException: If any regularity value is not between 0 and 1.
        """
        values = self.temporal_expression.evaluate()
        invalid_values = [value for value in values if not (0 <= value <= 1)]
        if invalid_values:
            msg = f"REGULARITY must evaluate to fractions between 0 and 1. " f"Invalid values: {invalid_values}"
            raise InvalidRegularity(message=msg)

    def get_subset(self, start_index: int, end_index: int) -> Self:
        """
        Returns a new Regularity object for the given index range.
        """
        period_evaluator = self.expression_evaluator.get_subset(
            start_index=start_index,
            end_index=end_index,
        )
        periods = period_evaluator.get_periods().periods

        new_target_period = Period(start=periods[0].start, end=periods[-1].end)

        return self.__class__(
            expression_evaluator=period_evaluator,
            target_period=new_target_period,
            expression_input=self.temporal_expression.expression,
        )
