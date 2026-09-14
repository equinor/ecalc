import numpy as np
from scipy.interpolate import interp1d

from libecalc.common.errors.exceptions import IllegalStateException
from libecalc.energy.energy_units.converters import GasTurbine
from libecalc.energy.models.convex_hull import FloatArray
from libecalc.energy.models.sampled_compressor import SampledCompressor


def get_invertible_fuel_power_samples(name: str, compressor: SampledCompressor) -> tuple[FloatArray, FloatArray]:
    """Deduplicated (fuel, power) samples, validated as strictly increasing in power."""
    samples = compressor.get_fuel_power_samples()
    if samples is None:
        raise IllegalStateException(f"'{name}': compressor has no power_interpolation_values to build a turbine from.")
    fuel_values, power_values = samples
    unique_pairs = np.unique(np.column_stack([fuel_values, power_values]), axis=0)
    sorted_fuel, sorted_power = unique_pairs[:, 0], unique_pairs[:, 1]
    if np.any(np.diff(sorted_power) <= 0):
        raise IllegalStateException(
            f"'{name}': power must be strictly increasing with fuel (after removing "
            f"exact-duplicate sample rows) to invert the fuel-to-power curve into a "
            f"power-to-fuel curve; got fuel={fuel_values.tolist()}, power={power_values.tolist()}."
        )
    return sorted_fuel, sorted_power


def build_gas_turbine(name: str, model: SampledCompressor) -> GasTurbine:
    """Build a GasTurbine converter dedicated to driving a fuel-driven SampledCompressor.

    Only applicable when the compressor was sampled with power_interpolation_values, i.e.
    the compressor represents a fuel-and-turbine unit where fuel usage is known directly
    (from the compressor's own curve) and power is reported alongside it, sampled at the
    same operating points. The (fuel, power) samples are inverted into a power -> fuel
    lookup for the dedicated turbine.
    """
    sorted_fuel, sorted_power = get_invertible_fuel_power_samples(name, model)
    power_to_fuel_function = interp1d(sorted_power, sorted_fuel, fill_value=(0, np.nan), bounds_error=False)

    return GasTurbine(
        name=name,
        power_to_fuel=lambda power: float(power_to_fuel_function(power)),
    )
