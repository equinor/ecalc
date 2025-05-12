from datetime import datetime

from libecalc.common.time_utils import Period
from libecalc.common.units import Unit
from libecalc.common.utils.rates import RateType, TimeSeriesRate
from libecalc.common.variables import ExpressionEvaluator, VariablesMap
from libecalc.domain.base_temporal_logic import BaseTemporalLogic
from libecalc.domain.regularity import Regularity
from libecalc.expression.expression import ExpressionType


class HydrocarbonExport(BaseTemporalLogic):
    """
    Represents the hydrocarbon export functionality for an installation.

    This class models the hydrocarbon export rates over a specified time period. It
    also incorporates regularity values to adjust the export rates.
    """

    def __init__(
        self,
        name: str,
        expression_evaluator: ExpressionEvaluator,
        regularity: Regularity,
        target_period: Period,
        expression: ExpressionType | dict[datetime, ExpressionType] | None = None,
    ):
        self.regularity = regularity
        super().__init__(name, expression_evaluator, target_period, expression)

    def default_expression_value(self) -> float:
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
            values=self.values,
            unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
            rate_type=RateType.CALENDAR_DAY,
            regularity=self.regularity.values,
        )

    @classmethod
    def create(
        cls,
        period: Period = None,
        expression_evaluator: ExpressionEvaluator = None,
        expression_value: ExpressionType = 1,
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
            regularity = Regularity.create(expression_evaluator=expression_evaluator, expression_value=1)

        return cls(
            name="default",
            expression=expression_value,
            target_period=expression_evaluator.get_period(),
            expression_evaluator=expression_evaluator,
            regularity=regularity,
        )
