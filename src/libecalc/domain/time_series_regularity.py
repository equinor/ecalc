from typing import Self, cast

from libecalc.common.time_utils import Period
from libecalc.common.units import Unit
from libecalc.common.utils.rates import TimeSeriesFloat
from libecalc.domain.component_validation_error import DomainValidationException
from libecalc.expression.temporal_expression import TemporalExpression


class InvalidRegularity(DomainValidationException): ...


class TimeSeriesRegularity:
    """
    Interface for evaluating regularity time series.

    Implementations should provide methods to evaluate and return
    regularity values as lists, for each stream day.
    """

    def __init__(self, timeseries: TimeSeriesFloat):
        self._timeseries = timeseries
        self.validate()
        # self._unit = Unit.NONE  # TODO: Fraction, or percentage?

    @classmethod
    def from_temporal_expression(cls, temporal_expression: TemporalExpression) -> Self:
        """
        TODO: Move out, as we do not want to have this dependency in domain
        Initializes the regularity time series from a temporal expression.
        """
        return TimeSeriesRegularity(
            TimeSeriesFloat(
                periods=temporal_expression.expression_evaluator.get_periods(),
                values=temporal_expression.evaluate(),
                unit=Unit.NONE,
            )
        )

    @property
    def values(self) -> list[float]:
        return self._timeseries.values

    @property
    def time_series(self) -> TimeSeriesFloat:  # TODO: Return Regularity timeseries or float timeseries?
        return self._timeseries

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
        # TODO: Should not expose and is too late to validate after instantiation
        invalid_values = [value for value in self.values if not (0 <= value <= 1)]
        if invalid_values:
            msg = f"REGULARITY must evaluate to fractions between 0 and 1. " f"Invalid values: {invalid_values}"
            raise InvalidRegularity(message=msg)

    def get_subset(self, period: Period) -> Self:
        return self.__class__(
            timeseries=cast(TimeSeriesFloat, self._timeseries.for_period(period)),
        )
