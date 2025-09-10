from libecalc.common.time_utils import Periods
from libecalc.domain.component_validation_error import DomainValidationException
from libecalc.domain.time_series_pressure import TimeSeriesPressure
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


class InvalidPressureException(DomainValidationException):
    """Exception raised for invalid pressure values."""

    def __init__(self, pressure: float, pressure_expression: str):
        if str(pressure) == pressure_expression:
            msg = f"All pressure values must be non-negative, got {pressure}."
        else:
            msg = f"All pressure values must be non-negative, got {pressure} in {pressure_expression}."
        super().__init__(message=msg)


class ExpressionTimeSeriesPressure(TimeSeriesPressure):
    """
    Provides pressure values by evaluating a time series expression.

    """

    def __init__(
        self,
        time_series_expression: TimeSeriesExpression,
        validation_mask: list[bool] | None = None,
    ):
        self._time_series_expression = time_series_expression
        self._pressure_values = self._time_series_expression.get_evaluated_expression()
        self._validation_mask = validation_mask
        self._validate()

    def _validate(self):
        """Validate that all pressure values are positive, except where masked by the condition."""
        if self._validation_mask is None:
            self._validation_mask = [True] * len(self._pressure_values)

        for pressure, should_validate in zip(self._pressure_values, self._validation_mask):
            if should_validate:
                # TODO: this comparison should in reality be <= 0, but since there are slight confusion around units
                #       bara vs barg in the input data, we allow 0 for now. Will be tightened up in future.
                if pressure < 0:
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

    def get_validation_mask(self) -> list[bool]:
        """
        Returns the mask indicating which pressure values were validated.

        """
        return self._validation_mask
