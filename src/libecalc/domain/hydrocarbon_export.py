from datetime import datetime

from libecalc.common.time_utils import Period
from libecalc.common.units import Unit
from libecalc.common.utils.rates import RateType, TimeSeriesRate
from libecalc.common.variables import ExpressionEvaluator, VariablesMap
from libecalc.domain.regularity import Regularity
from libecalc.expression.expression import ExpressionType
from libecalc.expression.temporal_expression import TemporalExpression


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
        self.temporal_expression = TemporalExpression(
            expression=expression_input or self.default_expression_value(),
            target_period=target_period,
            expression_evaluator=expression_evaluator,
        )
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

    @classmethod
    def create(
        cls,
        period: Period = None,
        expression_evaluator: ExpressionEvaluator = None,
        expression_input: ExpressionType = 0,
        regularity: Regularity = None,
    ):
        """
        Creates a default HydrocarbonExport instance with a given expression value and regularity.
        """
        if period and not expression_evaluator:
            expression_evaluator = VariablesMap(time_vector=[period.start, period.end])

        if not period and not expression_evaluator:
            expression_evaluator = VariablesMap(
                time_vector=[Period(datetime(1900, 1, 1)).start, Period(datetime(1900, 1, 1)).end]
            )

        if not regularity:
            regularity = Regularity.create(expression_evaluator=expression_evaluator, expression_input=1)

        return cls(
            expression_input=expression_input,
            target_period=expression_evaluator.get_period(),
            expression_evaluator=expression_evaluator,
            regularity=regularity,
        )
