import pytest

from libecalc.common.units import UnitConstants
from libecalc.domain.process.compressor.train.utils.common import (
    calculate_asv_corrected_rate,
    calculate_power_in_megawatt,
)
from libecalc.domain.process.compressor.train.utils.enthalpy_calculations import (
    _calculate_polytropic_exponent_expression_n_minus_1_over_n,
    calculate_outlet_pressure_campbell,
)


def test_calculate_polytropic_exponent_expression(
    test_data_compressor_train_common_shaft,
):
    for kappa, polytropic_efficiency in zip(
        test_data_compressor_train_common_shaft.kappa_values,
        test_data_compressor_train_common_shaft.polytropic_efficiency_values,
    ):
        assert _calculate_polytropic_exponent_expression_n_minus_1_over_n(
            kappa=kappa, polytropic_efficiency=polytropic_efficiency
        ) == (kappa - 1.0) / (kappa * polytropic_efficiency)


def test_calculate_outlet_pressure_campbell(
    test_data_compressor_train_common_shaft,
):
    # Use only the first element of each attribute of the fixture
    kappa = float(test_data_compressor_train_common_shaft.kappa_values[0])
    polytropic_efficiency = float(test_data_compressor_train_common_shaft.polytropic_efficiency_values[0])
    polytropic_head_fluid_Joule_per_kg = float(
        test_data_compressor_train_common_shaft.polytropic_head_fluid_Joule_per_kg_values[0]
    )
    molar_mass = float(test_data_compressor_train_common_shaft.molar_mass_values[0])
    z_inlet = float(test_data_compressor_train_common_shaft.z_inlet_values[0])
    inlet_temperature_K = float(test_data_compressor_train_common_shaft.inlet_temperature_K_values[0])
    inlet_pressure_bara = float(test_data_compressor_train_common_shaft.inlet_pressure_bara_values[0])

    polytropic_exponent_n_over_n_minus_1 = 1.0 / _calculate_polytropic_exponent_expression_n_minus_1_over_n(
        kappa=kappa,
        polytropic_efficiency=polytropic_efficiency,
    )
    pressure_fraction = (
        1.0
        + polytropic_head_fluid_Joule_per_kg
        / polytropic_exponent_n_over_n_minus_1
        * molar_mass
        / (z_inlet * UnitConstants.GAS_CONSTANT * inlet_temperature_K)
    ) ** (polytropic_exponent_n_over_n_minus_1)
    expected_outlet_pressure = inlet_pressure_bara * pressure_fraction

    result = calculate_outlet_pressure_campbell(
        kappa=kappa,
        polytropic_efficiency=polytropic_efficiency,
        inlet_pressure_bara=inlet_pressure_bara,
        molar_mass=molar_mass,
        z_inlet=z_inlet,
        inlet_temperature_K=inlet_temperature_K,
        polytropic_head_fluid_Joule_per_kg=polytropic_head_fluid_Joule_per_kg,
    )
    assert result == pytest.approx(expected_outlet_pressure)


def test_calculate_asv_corrected_rate():
    # Test when actual rate is larger than minimum
    actual_rate_m3_per_hour = 5
    density_kg_per_m3 = 10
    mass_rate_kg_per_hour = actual_rate_m3_per_hour * density_kg_per_m3
    (
        actual_rate_asv_corrected_m3_per_hour,
        mass_rate_asv_corrected_kg_per_hour,
    ) = calculate_asv_corrected_rate(
        actual_rate_m3_per_hour=actual_rate_m3_per_hour,
        minimum_actual_rate_m3_per_hour=3,
        density_kg_per_m3=density_kg_per_m3,
    )
    # Expect no change to rate du to asv
    assert actual_rate_asv_corrected_m3_per_hour == actual_rate_m3_per_hour
    assert mass_rate_asv_corrected_kg_per_hour == mass_rate_kg_per_hour

    # Test when actual rate is smaller than minimum
    minimum_actual_rate_m3_per_hour = 6
    (
        actual_rate_asv_corrected_m3_per_hour,
        mass_rate_asv_corrected_kg_per_hour,
    ) = calculate_asv_corrected_rate(
        actual_rate_m3_per_hour=actual_rate_m3_per_hour,
        minimum_actual_rate_m3_per_hour=minimum_actual_rate_m3_per_hour,
        density_kg_per_m3=density_kg_per_m3,
    )
    assert actual_rate_asv_corrected_m3_per_hour == minimum_actual_rate_m3_per_hour
    assert mass_rate_asv_corrected_kg_per_hour == minimum_actual_rate_m3_per_hour * density_kg_per_m3


def test_calculate_power_in_megawatt():
    mass_rate_kg_per_hour = 5
    enthalpy_change_joule_per_kg = 10.0
    power_megawatt = calculate_power_in_megawatt(
        mass_rate_kg_per_hour=mass_rate_kg_per_hour,
        enthalpy_change_joule_per_kg=enthalpy_change_joule_per_kg,
    )
    assert power_megawatt == (
        enthalpy_change_joule_per_kg
        * mass_rate_kg_per_hour
        / UnitConstants.SECONDS_PER_HOUR
        * UnitConstants.WATT_TO_MEGAWATT
    )
