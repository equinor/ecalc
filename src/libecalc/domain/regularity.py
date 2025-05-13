from datetime import datetime

from libecalc.common.time_utils import Period
from libecalc.common.units import Unit
from libecalc.common.utils.rates import TimeSeriesFloat
from libecalc.common.variables import ExpressionEvaluator, VariablesMap
from libecalc.domain.component_validation_error import ComponentValidationException, ModelValidationError
from libecalc.expression.expression import ExpressionType
from libecalc.expression.temporal_expression import TemporalExpression
from libecalc.presentation.yaml.validation_errors import Location


class Regularity:
    """
    Represents the regularity for an installation.

    This class models the regularity values over a specified time period,
    including validation to ensure they are valid fractions between 0 and 1.
    """

    def __init__(
        self,
        name: str,
        target_period: Period,
        expression_evaluator: ExpressionEvaluator,
        expression: ExpressionType | dict[datetime, ExpressionType] | None = None,
    ):
        self.name = name
        self.target_period = target_period
        self.expression_evaluator = expression_evaluator
        self.temporal_expression = TemporalExpression(
            expression=expression, target_period=target_period, expression_evaluator=expression_evaluator
        )
        self.validate()

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

    def default_expression_value(self) -> float:
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
            msg = (
                f"REGULARITY for component '{self.name}' must evaluate to fractions between 0 and 1. "
                f"Invalid values: {invalid_values}"
            )
            raise ComponentValidationException(
                errors=[
                    ModelValidationError(
                        name=self.name,
                        location=Location([self.name]),
                        message=msg,
                    )
                ],
            )

    @classmethod
    def create(
        cls,
        period: Period = None,
        expression_evaluator: ExpressionEvaluator = None,
        expression_value: ExpressionType = 1,
    ):
        """
        Creates a default Regularity instance with a given expression value.
        Mostly used for testing purposes.
        """
        if period and not expression_evaluator:
            expression_evaluator = VariablesMap(time_vector=[period.start, period.end])

        if not period and not expression_evaluator:
            expression_evaluator = VariablesMap(
                time_vector=[Period(datetime(1900, 1, 1)).start, Period(datetime(1900, 1, 1)).end]
            )

        return cls(
            name="default",
            expression=expression_value,
            target_period=expression_evaluator.get_period(),
            expression_evaluator=expression_evaluator,
        )
