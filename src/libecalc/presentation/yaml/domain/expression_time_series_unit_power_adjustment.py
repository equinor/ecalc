from libecalc.domain.time_series_unit_power_adjustment import TimeSeriesUnitPowerAdjustment
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


class ExpressionTimeSeriesUnitPowerAdjustmentFactor(TimeSeriesUnitPowerAdjustment):
    """
    Provides unit power adjustment factor values by evaluating a time series expression.
    """

    def __init__(self, time_series_expression: TimeSeriesExpression):
        self._time_series_expression = time_series_expression

    def get_values(self) -> list[float]:
        efficiency_loss_factor_values = self._time_series_expression.get_evaluated_expression()
        if efficiency_loss_factor_values is None:
            return [1.0] * len(self._time_series_expression.expression_evaluator.periods)
        return efficiency_loss_factor_values


class ExpressionTimeSeriesUnitPowerAdjustmentConstant(TimeSeriesUnitPowerAdjustment):
    """
    Provides unit power adjustment factor values by evaluating a time series expression.
    """

    def __init__(self, time_series_expression: TimeSeriesExpression):
        self._time_series_expression = time_series_expression

    def get_values(self) -> list[float]:
        efficiency_loss_constant_values = self._time_series_expression.get_evaluated_expression()
        if efficiency_loss_constant_values is None:
            return [0.0] * len(self._time_series_expression.expression_evaluator.get_periods())
        return efficiency_loss_constant_values
