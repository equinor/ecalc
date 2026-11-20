from libecalc.common.ddd import value_object
from libecalc.common.time_utils import Period
from libecalc.ecalc_model.validation import InvalidEcalcModelException, require_positive
from libecalc.presentation.yaml.domain.expression_time_series_flow_rate import ExpressionTimeSeriesFlowRate
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


@value_object
class TimeSeriesLiquidStream:
    volumetric_rate_m3_per_day: ExpressionTimeSeriesFlowRate
    pressure_bara: TimeSeriesExpression
    density_kg_per_m3: TimeSeriesExpression

    def __post_init__(self) -> None:
        rate_periods = self.volumetric_rate_m3_per_day.get_periods().periods
        if not (rate_periods == self.pressure_bara.get_periods() == self.density_kg_per_m3.get_periods()):
            raise InvalidEcalcModelException(
                "Liquid stream rate, pressure and density must be defined for the same periods."
            )
        require_positive(self.pressure_bara, "Liquid stream pressure [bara]")
        require_positive(self.density_kg_per_m3, "Liquid stream density [kg/m3]")

    def get_periods(self) -> list[Period]:
        return self.volumetric_rate_m3_per_day.get_periods().periods
