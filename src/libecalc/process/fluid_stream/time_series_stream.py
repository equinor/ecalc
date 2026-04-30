from dataclasses import dataclass

from libecalc.presentation.yaml.domain.expression_time_series_flow_rate import ExpressionTimeSeriesFlowRate
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression
from libecalc.process.fluid_stream.fluid_model import FluidModel


@dataclass(frozen=True)
class TimeSeriesStream:
    fluid_model: FluidModel
    pressure_bara: TimeSeriesExpression
    temperature_kelvin: TimeSeriesExpression
    standard_rate_m3_per_day: ExpressionTimeSeriesFlowRate
