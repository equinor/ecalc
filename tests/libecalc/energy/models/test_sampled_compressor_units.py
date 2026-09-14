import math

import pytest

from libecalc.common.errors.exceptions import IllegalStateException
from libecalc.energy.models.sampled_compressor import SampledCompressor
from libecalc.energy.models.sampled_compressor_units import build_gas_turbine


class TestBuildGasTurbine:
    def test_builds_turbine_with_power_to_fuel_curve_from_paired_samples(self):
        compressor = SampledCompressor(
            energy_usage_values=[1000.0, 2000.0, 3000.0],
            rate_values=[0.0, 100.0, 200.0],
            power_interpolation_values=[1.0, 2.0, 3.0],
        )
        turbine = build_gas_turbine("compressor-turbine", compressor)

        assert turbine.get_name() == "compressor-turbine"
        assert turbine.get_input_energy(turbine.get_output_energy_type()(1.5)).value == pytest.approx(1500.0)

    def test_power_to_fuel_extrapolates_below_and_undefined_above_sampled_range(self):
        # Matches legacy's turbine mapping: below the minimum sampled power the turbine
        # is idling (0 fuel), above the maximum sampled power it is undefined (NaN).
        compressor = SampledCompressor(
            energy_usage_values=[1000.0, 2000.0],
            rate_values=[0.0, 100.0],
            power_interpolation_values=[1.0, 2.0],
        )
        turbine = build_gas_turbine("t", compressor)
        power_type = turbine.get_output_energy_type()

        assert turbine.get_input_energy(power_type(0.1)).value == pytest.approx(0.0)
        assert math.isnan(turbine.get_input_energy(power_type(5.0)).value)

    def test_raises_when_no_power_interpolation(self):
        compressor = SampledCompressor(
            energy_usage_values=[1000.0, 2000.0],
            rate_values=[0.0, 100.0],
        )
        with pytest.raises(IllegalStateException, match="no power_interpolation_values"):
            build_gas_turbine("t", compressor)

    def test_raises_when_power_not_strictly_increasing_with_fuel(self):
        compressor = SampledCompressor(
            energy_usage_values=[1000.0, 2000.0, 3000.0],
            rate_values=[0.0, 100.0, 200.0],
            power_interpolation_values=[1.0, 1.0, 0.5],
        )
        with pytest.raises(IllegalStateException, match="must be strictly increasing"):
            build_gas_turbine("t", compressor)
