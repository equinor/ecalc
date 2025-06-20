from libecalc.domain.process.dto.consumer_system import SystemOperationalSetting
from libecalc.expression import Expression


def map_discharge_pressures(
    operational_setting: SystemOperationalSetting,
    number_of_consumers: int,
) -> list[Expression]:
    if operational_setting.discharge_pressure is not None:
        return [operational_setting.discharge_pressure] * number_of_consumers  # type: ignore[list-item]
    elif operational_setting.discharge_pressures is not None:
        return operational_setting.discharge_pressures
    else:
        # If not specified, default to zero-expression.
        return [Expression.setup_from_expression(0)] * number_of_consumers


def map_suction_pressures(operational_setting: SystemOperationalSetting, number_of_consumers: int) -> list[Expression]:
    if operational_setting.suction_pressure is not None:
        return [operational_setting.suction_pressure] * number_of_consumers  # type: ignore[list-item]
    elif operational_setting.suction_pressures is not None:
        return operational_setting.suction_pressures
    else:
        # If not specified, default to zero-expression.
        return [Expression.setup_from_expression(0)] * number_of_consumers


def map_rates(
    operational_setting: SystemOperationalSetting,
    system_rate: Expression | None,
    number_of_consumers: int,
) -> list[Expression]:
    if operational_setting.rates is not None:
        return operational_setting.rates
    elif operational_setting.rate_fractions:
        # Multiply rate_fractions with total system rate to get rates
        return [
            Expression.multiply(
                system_rate,  # type: ignore[arg-type]
                rate_fraction,  # type: ignore[arg-type]
            )
            for rate_fraction in operational_setting.rate_fractions
        ]
    else:
        # If not specified, default to zero-expression.
        return [Expression.setup_from_expression(0)] * number_of_consumers
