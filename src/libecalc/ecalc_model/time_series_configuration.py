from libecalc.common.ddd import value_object
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


@value_object
class TimeSeriesChokeConfiguration:
    delta_pressure: TimeSeriesExpression


@value_object
class TimeSeriesTemperatureSetterConfiguration:
    temperature_in_celsius: TimeSeriesExpression
