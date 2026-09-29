import math

from libecalc.common.time_utils import Period
from libecalc.energy.energy_types import Energy
from libecalc.energy.errors import InvalidEnergyNetworkInputError
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


def _evaluate(expression: TimeSeriesExpression, *, period: Period, description: str) -> float:
    try:
        return float(expression.get_value(period))
    except KeyError as error:
        raise InvalidEnergyNetworkInputError(f"{description} has no value for period {period}") from error


def resolve_non_negative(expression: TimeSeriesExpression, *, period: Period, description: str) -> float:
    value = _evaluate(expression, period=period, description=description)
    if not math.isfinite(value) or value < 0:
        raise InvalidEnergyNetworkInputError(
            f"{description} must be finite and non-negative, got {value} for period {period}"
        )
    return value


def resolve_energy(
    expression: TimeSeriesExpression,
    energy_type: type[Energy],
    *,
    period: Period,
    description: str,
) -> Energy:
    return energy_type(resolve_non_negative(expression, period=period, description=description))


def resolve_optional_energy(
    expression: TimeSeriesExpression | None,
    energy_type: type[Energy],
    *,
    period: Period,
    description: str,
) -> Energy | None:
    if expression is None:
        return None
    return resolve_energy(expression, energy_type, period=period, description=description)


def resolve_optional_value(
    expression: TimeSeriesExpression | None, *, period: Period, description: str
) -> float | None:
    if expression is None:
        return None
    value = _evaluate(expression, period=period, description=description)
    if not math.isfinite(value):
        raise InvalidEnergyNetworkInputError(f"{description} must be finite, got {value} for period {period}")
    return value
