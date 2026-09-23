import math

from libecalc.common.time_utils import Period
from libecalc.energy.energy_types import Energy
from libecalc.energy.errors import InvalidEnergyNetworkInputError
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression


def resolve_energy(
    expression: TimeSeriesExpression,
    energy_type: type[Energy],
    *,
    period: Period | None,
    description: str,
) -> Energy:
    """Evaluate a non-negative energy expression for `period`, as `energy_type`."""
    if not isinstance(period, Period):
        raise InvalidEnergyNetworkInputError(
            f"{description} is an expression and needs a period to be evaluated, got {period!r}"
        )

    try:
        value = float(expression.get_value(period))
    except KeyError as error:
        raise InvalidEnergyNetworkInputError(f"{description} has no value for period {period}") from error

    if not math.isfinite(value) or value < 0:
        raise InvalidEnergyNetworkInputError(
            f"{description} must be finite and non-negative, got {value} for period {period}"
        )
    return energy_type(value)


def resolve_optional_energy(
    expression: TimeSeriesExpression | None,
    energy_type: type[Energy],
    *,
    period: Period | None,
    description: str,
) -> Energy | None:
    if expression is None:
        return None
    return resolve_energy(expression, energy_type, period=period, description=description)
