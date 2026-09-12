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

    def test_power_to_fuel_clamps_below_and_undefined_above_sampled_range(self):
        # Below the minimum sampled power, fuel is clamped to the minimum sample's fuel
        # value (the minimum is just the lowest point we have data for, not a true floor,
        # so this avoids reporting free/zero fuel for demand below it). Above the maximum
        # sampled power (a real physical capacity limit) fuel is undefined (NaN).
        compressor = SampledCompressor(
            energy_usage_values=[1000.0, 2000.0],
            rate_values=[0.0, 100.0],
            power_interpolation_values=[1.0, 2.0],
        )
        turbine = build_gas_turbine("t", compressor)
        power_type = turbine.get_output_energy_type()

        assert turbine.get_input_energy(power_type(0.1)).value == pytest.approx(1000.0)
        assert math.isnan(turbine.get_input_energy(power_type(5.0)).value)

    def test_power_to_fuel_reports_zero_fuel_when_compressor_is_off(self):
        # power=0 means the paired compressor is switched off (SampledCompressor.evaluate
        # returns energy_usage=power=0.0 for rate<=0) - the turbine must report zero fuel
        # for that, not the minimum-power clamp used for 0 < power < min sampled power.
        compressor = SampledCompressor(
            energy_usage_values=[1000.0, 2000.0, 3000.0],
            rate_values=[10.0, 100.0, 200.0],
            power_interpolation_values=[1.0, 2.0, 3.0],
        )
        turbine = build_gas_turbine("t", compressor)
        power_type = turbine.get_output_energy_type()

        assert turbine.get_input_energy(power_type(0.0)).value == pytest.approx(0.0)

    def test_raises_when_no_power_interpolation(self):
        compressor = SampledCompressor(
            energy_usage_values=[1000.0, 2000.0],
            rate_values=[0.0, 100.0],
        )
        with pytest.raises(IllegalStateException, match="no power_interpolation_values"):
            build_gas_turbine("t", compressor)

    def test_raises_when_power_not_strictly_increasing_with_fuel(self):
        with pytest.raises(IllegalStateException, match="strictly monotonic"):
            SampledCompressor(
                energy_usage_values=[1000.0, 2000.0, 3000.0],
                rate_values=[0.0, 100.0, 200.0],
                power_interpolation_values=[1.0, 1.0, 0.5],
            )
