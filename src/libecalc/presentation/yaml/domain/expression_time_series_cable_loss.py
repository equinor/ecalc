from datetime import datetime

from libecalc.common.time_utils import Periods
from libecalc.domain.time_series_cable_loss import TimeSeriesCableLoss
from libecalc.dto.types import ConsumerUserDefinedCategoryType
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression
from libecalc.presentation.yaml.yaml_types.yaml_temporal_model import YamlTemporalModel


class ExpressionTimeSeriesCableLoss(TimeSeriesCableLoss):
    """
    Provides cable loss values by evaluating a time series expression.
    Only applies cable loss when the category is POWER_FROM_SHORE; otherwise, returns 0.
    """

    def __init__(
        self, time_series_expression: TimeSeriesExpression, category: YamlTemporalModel[ConsumerUserDefinedCategoryType]
    ):
        self._time_series_expression = time_series_expression
        self._category = category

    def get_values(self) -> list[float]:
        # Evaluate the cable loss expression for all periods (returns a list of values)
        cable_loss_values = self._time_series_expression.get_evaluated_expressions()
        periods = self.get_periods()
        category_model = self._category

        # Handle both single value and dict (temporal) cases
        if isinstance(category_model, dict):
            # Sort change points by datetime
            change_points = sorted(category_model.items())
        else:
            # Single value for all periods
            change_points = [(datetime(1900, 1, 1), category_model)]

        result = []
        change_idx = 0

        for idx, period in enumerate(periods):
            # Advance to the correct category for this period
            while change_idx + 1 < len(change_points) and period.start >= change_points[change_idx + 1][0]:
                change_idx += 1
            current_category = change_points[change_idx][1]

            if current_category == ConsumerUserDefinedCategoryType.POWER_FROM_SHORE:
                result.append(cable_loss_values[idx])
            else:
                result.append(0.0)
        return result

    def get_periods(self) -> Periods:
        """
        Returns the periods associated with the time series expression.
        Used to align cable loss values with the correct periods.
        """
        return self._time_series_expression.expression_evaluator.get_periods()
