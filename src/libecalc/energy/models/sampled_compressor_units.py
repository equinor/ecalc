import numpy as np
from scipy.interpolate import interp1d

from libecalc.common.errors.exceptions import IllegalStateException
from libecalc.energy.energy_units.converters import GasTurbine
from libecalc.energy.models.convex_hull import FloatArray
from libecalc.energy.models.sampled_compressor import SampledCompressor


def get_invertible_fuel_power_samples(name: str, compressor: SampledCompressor) -> tuple[FloatArray, FloatArray]:
    """The compressor's sorted, strictly-monotonic (fuel, power) samples - already
    validated by SampledCompressor itself, so this only re-raises the "no power
    samples" case with a turbine-specific message."""
    samples = compressor._get_fuel_power_samples()
    if samples is None:
        raise IllegalStateException(f"'{name}': compressor has no power_interpolation_values to build a turbine from.")
    return samples


def build_gas_turbine(name: str, model: SampledCompressor) -> GasTurbine:
    """Build a GasTurbine converter dedicated to driving a fuel-driven SampledCompressor,
    inverting its (fuel, power) samples into a power -> fuel lookup."""
    sorted_fuel, sorted_power = get_invertible_fuel_power_samples(name, model)
    # Below the minimum sampled power, clamp to the minimum sample's fuel value rather
    # than extrapolating - it's just the lowest point we have data for, not necessarily
    # a true operating floor. Above the maximum (a real physical capacity limit), fuel
    # is left NaN - infeasible demand, must be rejected rather than approximated.
    power_to_fuel_function = interp1d(
        sorted_power, sorted_fuel, fill_value=(sorted_fuel[0], np.nan), bounds_error=False
    )

    def power_to_fuel(power: float) -> float:
        # power<=0 means the compressor is off (SampledCompressor.evaluate returns
        # energy_usage=power=0.0 for rate<=0) - must be zero fuel, not the min-power
        # clamp above.
        if power <= 0:
            return 0.0
        return float(power_to_fuel_function(power))

    return GasTurbine(
        name=name,
        power_to_fuel=power_to_fuel,
    )
