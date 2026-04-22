from dataclasses import dataclass

from libecalc.domain.process.value_objects.fluid_stream import EoSModel
from libecalc.presentation.yaml.domain.expression_time_series_flow_rate import ExpressionTimeSeriesFlowRate
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


@dataclass(frozen=True)
class TimeSeriesStream:
    eos_model: EoSModel  # TODO: Fixed, but is a "strategy" and should be provided as a strategy. Should we support different eos models for different problems/trains?
    composition: (
        TimeSeriesExpression  # currently considered timeseries property of a stream, not related to "domain events"
    )
    pressure_bara: TimeSeriesExpression
    temperature_kelvin: TimeSeriesExpression
    standard_rate_m3_per_day: ExpressionTimeSeriesFlowRate
