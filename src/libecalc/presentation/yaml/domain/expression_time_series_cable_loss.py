from libecalc.common.logger import logger
from libecalc.common.temporal_model import TemporalModel
from libecalc.common.time_utils import Periods
from libecalc.domain.time_series_cable_loss import TimeSeriesCableLoss
from libecalc.dto.types import ConsumerUserDefinedCategoryType
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


class ExpressionTimeSeriesCableLoss(TimeSeriesCableLoss):
    """
    Provides cable loss values by evaluating a time series expression.
    Only applies cable loss when the category is POWER_FROM_SHORE; otherwise, returns 0.
    """

    def __init__(
        self, time_series_expression: TimeSeriesExpression, category: TemporalModel[ConsumerUserDefinedCategoryType]
    ):
        self._time_series_expression = time_series_expression
        self._category = category

    def get_values(self) -> list[float]:
        # Evaluate the cable loss expression for all periods (returns a list of values)
        cable_loss_values = self._time_series_expression.get_evaluated_expressions()
        periods = self.get_periods()

        result = []

        for period, cable_loss in zip(periods, cable_loss_values):
            try:
                if self._category.get_model(period) == ConsumerUserDefinedCategoryType.POWER_FROM_SHORE:
                    result.append(cable_loss)
                else:
                    result.append(0.0)
            except ValueError:
                logger.warning(
                    f"Temporal model for generator set category is not defined for period {period}. Assuming 0.0 cable loss."
                )
                result.append(0.0)
        return result

    def get_periods(self) -> Periods:
        """
        Returns the periods associated with the time series expression.
        Used to align cable loss values with the correct periods.
        """
        return self._time_series_expression.expression_evaluator.get_periods()
