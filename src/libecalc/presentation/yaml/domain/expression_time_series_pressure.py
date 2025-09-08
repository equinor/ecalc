from libecalc.common.time_utils import Periods
from libecalc.domain.component_validation_error import DomainValidationException
from libecalc.domain.time_series_pressure import TimeSeriesPressure
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


class InvalidPressureException(DomainValidationException):
    """Exception raised for invalid pressure values."""

    def __init__(self, pressure: float, pressure_expression: str):
        if str(pressure) == pressure_expression:
            msg = f"All pressure values must be positive, got {pressure}."
        else:
            msg = f"All pressure values must be positive, got {pressure} in {pressure_expression}."
        super().__init__(message=msg)


class ExpressionTimeSeriesPressure(TimeSeriesPressure):
    """
    Provides pressure values by evaluating a time series expression.

    """

    def __init__(
        self,
        time_series_expression: TimeSeriesExpression,
    ):
        self._time_series_expression = time_series_expression
        self._pressure_values = self._time_series_expression.get_evaluated_expression()
        self._validate()

    def _validate(self):
        """Validate that all pressure values are positive."""
        for pressure in self._pressure_values:
            if pressure <= 0:
                raise InvalidPressureException(pressure, str(self._time_series_expression.get_expression()))

    def get_periods(self) -> Periods:
        """
        Returns the periods associated with the time series expression.

        This is used to align the flow rate values with the corresponding periods.
        """
        return self._time_series_expression.expression_evaluator.get_periods()

    def get_values(self) -> list[float]:
        """
        Returns the pressure values as a list.

        """

        pressure_values = self._pressure_values

        return list(pressure_values)
