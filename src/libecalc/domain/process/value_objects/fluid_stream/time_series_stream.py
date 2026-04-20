from dataclasses import dataclass

from libecalc.domain.process.value_objects.fluid_stream import FluidModel
from libecalc.presentation.yaml.domain.expression_time_series_flow_rate import ExpressionTimeSeriesFlowRate
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


@dataclass(frozen=True)
class TimeSeriesStream:
    fluid_model: FluidModel
    pressure_bara: TimeSeriesExpression
    temperature_kelvin: TimeSeriesExpression
    standard_rate_m3_per_day: ExpressionTimeSeriesFlowRate
