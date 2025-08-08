from datetime import datetime

from libecalc.common.time_utils import Period
from libecalc.common.units import Unit
from libecalc.common.utils.rates import RateType, TimeSeriesRate
from libecalc.common.variables import ExpressionEvaluator
from libecalc.domain.regularity import Regularity
from libecalc.expression.expression import ExpressionType, InvalidExpressionError
from libecalc.expression.temporal_expression import TemporalExpression


class InvalidHydrocarbonExport(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class HydrocarbonExport:
    """
    Represents the hydrocarbon export functionality for an installation.

    This class models the hydrocarbon export rates over a specified time period. It
    also incorporates regularity values to adjust the export rates.
    """

    def __init__(
        self,
        expression_evaluator: ExpressionEvaluator,
        regularity: Regularity,
        target_period: Period,
        expression_input: ExpressionType | dict[datetime, ExpressionType] | None = None,
    ):
        self.expression_evaluator = expression_evaluator
        self.target_period = target_period
        try:
            self.temporal_expression = TemporalExpression(
                expression=expression_input or self.default_expression_value(),
                target_period=target_period,
                expression_evaluator=expression_evaluator,
            )
        except (ValueError, InvalidExpressionError) as e:
            raise InvalidHydrocarbonExport(str(e)) from e
        self.regularity = regularity

    @staticmethod
    def default_expression_value() -> float:
        """
        Returns the default expression value for HydrocarbonExport.
        """
        return 0

    @property
    def time_series(self) -> TimeSeriesRate:
        """
        Returns the evaluated hydrocarbon export rates as a time series.

        Returns:
            TimeSeriesRate: A time series mapping each time period to its evaluated hydrocarbon export rate.
        """
        return TimeSeriesRate(
            periods=self.expression_evaluator.get_periods(),
            values=self.temporal_expression.evaluate(),
            unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
            rate_type=RateType.CALENDAR_DAY,
            regularity=self.regularity.time_series.values,
        )
