from libecalc.common.errors.exceptions import InvalidColumnException
from libecalc.domain.resource import Resource
from libecalc.energy.models.sampled_compressor import SampledCompressor

RATE_HEADER = "RATE"
SUCTION_PRESSURE_HEADER = "SUCTION_PRESSURE"
DISCHARGE_PRESSURE_HEADER = "DISCHARGE_PRESSURE"
FUEL_HEADER = "FUEL"
POWER_HEADER = "POWER"

_VARIABLE_HEADERS = (RATE_HEADER, SUCTION_PRESSURE_HEADER, DISCHARGE_PRESSURE_HEADER)


def build_sampled_compressor_model(resource: Resource) -> SampledCompressor:
    """Parse a tabular Resource into a SampledCompressor model.

    Expected columns (case-insensitive, at least one of the three variables plus
    at least one of FUEL/POWER):
        RATE, SUCTION_PRESSURE, DISCHARGE_PRESSURE (independent variables, any subset)
        FUEL: the sampled fuel usage (Sm3/d). Primary energy usage when present.
        POWER: the sampled power (MW). Primary energy usage when FUEL is absent;
            when both FUEL and POWER are present, POWER is instead treated as data
            sampled at the same operating points, used to derive a dedicated
            turbine's power-to-fuel curve.
    """
    headers = {header.upper() for header in resource.get_headers()}

    variable_headers = [header for header in _VARIABLE_HEADERS if header in headers]
    if not variable_headers:
        raise InvalidColumnException(
            header=RATE_HEADER,
            message=f"Sampled compressor resource must contain at least one of: {', '.join(_VARIABLE_HEADERS)}.",
        )

    has_fuel = FUEL_HEADER in headers
    has_power = POWER_HEADER in headers
    if not has_fuel and not has_power:
        raise InvalidColumnException(
            header=FUEL_HEADER,
            message="Sampled compressor resource must contain FUEL, POWER, or both.",
        )

    if has_fuel:
        energy_usage_values = resource.get_float_column(FUEL_HEADER)
        power_interpolation_values = resource.get_float_column(POWER_HEADER) if has_power else None
    else:
        energy_usage_values = resource.get_float_column(POWER_HEADER)
        power_interpolation_values = None

    return SampledCompressor(
        energy_usage_values=energy_usage_values,
        rate_values=resource.get_float_column(RATE_HEADER) if RATE_HEADER in headers else None,
        suction_pressure_values=(
            resource.get_float_column(SUCTION_PRESSURE_HEADER) if SUCTION_PRESSURE_HEADER in headers else None
        ),
        discharge_pressure_values=(
            resource.get_float_column(DISCHARGE_PRESSURE_HEADER) if DISCHARGE_PRESSURE_HEADER in headers else None
        ),
        power_interpolation_values=power_interpolation_values,
    )
