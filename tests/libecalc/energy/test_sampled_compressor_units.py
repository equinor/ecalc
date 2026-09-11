"""Tests for building persistent network units from a sampled-compressor model, and for
deriving each timestep's consumer demand from a resolved evaluation."""

import pytest

from libecalc.common.errors.exceptions import IllegalStateException
from libecalc.energy.energy_types import ElectricalPower, FuelGasRate, MechanicalPower
from libecalc.energy.energy_units.consumers import ElectricalConsumer, FuelGasConsumer, MechanicalConsumer
from libecalc.energy.energy_units.converters import GasTurbine
from libecalc.energy.models.sampled_compressor import SampledCompressor, SampledCompressorResult
from libecalc.energy.models.sampled_compressor_units import (
    build_gas_turbine,
    build_sampled_compressor_units,
    sampled_compressor_demand,
)


def _compressor(power_interpolation_values: list[float] | None) -> SampledCompressor:
    return SampledCompressor(
        energy_usage_values=[100.0, 150.0, 200.0],
        rate_values=[10.0, 15.0, 20.0],
        power_interpolation_values=power_interpolation_values,
    )


class TestBuildSampledCompressorUnits:
    def test_fuel_only_builds_fuel_gas_consumer(self):
        result = build_sampled_compressor_units("compressor", _compressor(None), consumes_fuel=True)
        assert isinstance(result, FuelGasConsumer)

    def test_power_only_builds_electrical_consumer(self):
        result = build_sampled_compressor_units("compressor", _compressor(None), consumes_fuel=False)
        assert isinstance(result, ElectricalConsumer)

    def test_fuel_and_power_builds_turbine_consumer_pair(self):
        result = build_sampled_compressor_units("compressor", _compressor([1.0, 1.5, 2.0]), consumes_fuel=True)
        assert isinstance(result, tuple)
        converter, consumer = result
        assert isinstance(converter, GasTurbine)
        assert isinstance(consumer, MechanicalConsumer)


class TestBuildGasTurbine:
    def test_max_power_matches_highest_sample(self):
        turbine = build_gas_turbine("turbine", _compressor([1.0, 1.5, 2.0]))
        assert turbine.get_max_power() == 2.0

    def test_inverts_the_forward_fuel_to_power_curve(self):
        compressor = _compressor([1.0, 1.5, 2.0])
        turbine = build_gas_turbine("turbine", compressor)
        for fuel, power in zip([100.0, 150.0, 200.0], [1.0, 1.5, 2.0], strict=True):
            assert turbine.get_input_energy(MechanicalPower(power)).value == pytest.approx(fuel)

    def test_round_trip_matches_compressor_evaluation(self):
        # The turbine's inverse must recover the exact fuel the compressor itself
        # resolved for a given operating point - not just at the sample points - since
        # both directions are built from the same underlying samples (see
        # SampledCompressor.get_fuel_power_samples).
        compressor = _compressor([1.0, 1.5, 2.0])
        turbine = build_gas_turbine("turbine", compressor)
        for rate in [10.0, 12.5, 15.0, 17.5, 20.0]:
            result = compressor.evaluate(rate=rate)
            assert result.power is not None
            recovered_fuel = turbine.get_input_energy(MechanicalPower(result.power)).value
            assert recovered_fuel == pytest.approx(result.energy_usage)

    def test_no_power_interpolation_values_raises(self):
        with pytest.raises(IllegalStateException):
            build_gas_turbine("turbine", _compressor(None))

    def test_non_invertible_power_raises(self):
        # power does not strictly increase with fuel - e.g. real gascompression.csv
        # fixture data, where POWER is a coarse reporting flag, not a genuine function
        # of FUEL.
        compressor = _compressor([1.0, 1.0, 1.0])
        with pytest.raises(IllegalStateException):
            build_gas_turbine("turbine", compressor)

    def test_exact_duplicate_rows_are_deduplicated_and_accepted(self):
        """A repeated (fuel, power) sample pair is not a genuine non-invertibility -
        get_invertible_fuel_power_samples dedupes exact row duplicates before checking
        strict monotonicity. Two distinct rates mapping to the same (fuel, power) pair
        (a flat plateau) reproduces this without violating SampledCompressor's own
        unique-RATE requirement."""
        compressor = SampledCompressor(
            energy_usage_values=[100.0, 100.0, 150.0, 200.0],
            rate_values=[10.0, 11.0, 15.0, 20.0],
            power_interpolation_values=[1.0, 1.0, 1.5, 2.0],
        )
        turbine = build_gas_turbine("turbine", compressor)
        assert turbine.get_input_energy(MechanicalPower(1.0)).value == pytest.approx(100.0)

    def test_zero_power_maps_to_zero_fuel(self):
        """Below the lowest sampled power, get_input_energy must return 0 fuel (an idle
        turbine consuming no fuel), not NaN or an extrapolated negative value."""
        turbine = build_gas_turbine("turbine", _compressor([1.0, 1.5, 2.0]))
        assert turbine.get_input_energy(MechanicalPower(0.0)).value == pytest.approx(0.0)


class TestSampledCompressorDemand:
    def test_fuel_only_returns_fuel_gas_rate(self):
        demand = sampled_compressor_demand(SampledCompressorResult(energy_usage=123.4), consumes_fuel=True)
        assert demand == FuelGasRate(123.4)

    def test_power_only_returns_electrical_power(self):
        demand = sampled_compressor_demand(SampledCompressorResult(energy_usage=5.6), consumes_fuel=False)
        assert demand == ElectricalPower(5.6)

    def test_fuel_and_power_returns_mechanical_power_for_the_turbine_pair(self):
        demand = sampled_compressor_demand(SampledCompressorResult(energy_usage=150.0, power=1.5), consumes_fuel=True)
        assert demand == MechanicalPower(1.5)
