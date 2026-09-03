"""Builds libecalc.energy network units for one sampled-compressor model."""

import numpy as np
from scipy.interpolate import interp1d

from libecalc.common.errors.exceptions import IllegalStateException
from libecalc.energy.consumer import Consumer
from libecalc.energy.converter import Converter
from libecalc.energy.energy_types import ElectricalPower, Energy, FuelGasRate, MechanicalPower
from libecalc.energy.energy_units.consumers import ElectricalConsumer, FuelGasConsumer, MechanicalConsumer
from libecalc.energy.energy_units.converters import GasTurbine
from libecalc.energy.models.convex_hull import FloatArray
from libecalc.energy.models.sampled_compressor import SampledCompressor, SampledCompressorResult


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


def build_gas_turbine(name: str, compressor: SampledCompressor) -> GasTurbine:
    """Builds the fuel -> power converter for a compressor model with POWER data."""
    sorted_fuel, sorted_power = get_invertible_fuel_power_samples(name, compressor)
    power_to_fuel_function = interp1d(sorted_power, sorted_fuel, fill_value=(0, np.nan), bounds_error=False)
    return GasTurbine(
        name=name,
        max_power=float(sorted_power[-1]),
        power_to_fuel=lambda power: float(power_to_fuel_function(power)),
    )


def build_sampled_compressor_units(
    name: str, compressor: SampledCompressor, consumes_fuel: bool
) -> Consumer | tuple[Converter, Consumer]:
    """Builds the persistent network unit(s) for one compressor-sampled model."""
    if consumes_fuel and compressor.get_fuel_power_samples() is not None:
        return build_gas_turbine(name, compressor), MechanicalConsumer(name)
    if consumes_fuel:
        return FuelGasConsumer(name)
    return ElectricalConsumer(name)


def sampled_compressor_demand(result: SampledCompressorResult, consumes_fuel: bool) -> Energy:
    """The Energy demand for the terminal consumer, from a resolved evaluation."""
    if consumes_fuel and result.power is not None:
        return MechanicalPower(result.power)
    return FuelGasRate(result.energy_usage) if consumes_fuel else ElectricalPower(result.energy_usage)
