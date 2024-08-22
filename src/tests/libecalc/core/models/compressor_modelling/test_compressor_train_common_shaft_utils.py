import numpy as np
import pytest

from libecalc.common.units import UnitConstants
from libecalc.core.models.compressor.train.utils.common import (
    calculate_asv_corrected_rate,
    calculate_power_in_megawatt,
)
from libecalc.core.models.compressor.train.utils.enthalpy_calculations import (
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
    polytropic_exponents_n_over_n_minus_1 = 1.0 / _calculate_polytropic_exponent_expression_n_minus_1_over_n(
        kappa=test_data_compressor_train_common_shaft.kappa_values,
        polytropic_efficiency=test_data_compressor_train_common_shaft.polytropic_efficiency_values,
    )
    pressure_fraction = (
        1.0
        + test_data_compressor_train_common_shaft.polytropic_head_fluid_Joule_per_kg_values
        / polytropic_exponents_n_over_n_minus_1
        * test_data_compressor_train_common_shaft.molar_mass_values
        / (
            test_data_compressor_train_common_shaft.z_inlet_values
            * UnitConstants.GAS_CONSTANT
            * test_data_compressor_train_common_shaft.inlet_temperature_K_values
        )
    ) ** (polytropic_exponents_n_over_n_minus_1)
    outlet_pressure_bara_values = test_data_compressor_train_common_shaft.inlet_pressure_bara_values * pressure_fraction
    np.testing.assert_allclose(
        calculate_outlet_pressure_campbell(
            kappa=test_data_compressor_train_common_shaft.kappa_values,
            polytropic_efficiency=test_data_compressor_train_common_shaft.polytropic_efficiency_values,
            inlet_pressure_bara=test_data_compressor_train_common_shaft.inlet_pressure_bara_values,
            molar_mass=test_data_compressor_train_common_shaft.molar_mass_values,
            z_inlet=test_data_compressor_train_common_shaft.z_inlet_values,
            inlet_temperature_K=test_data_compressor_train_common_shaft.inlet_temperature_K_values,
            polytropic_head_fluid_Joule_per_kg=test_data_compressor_train_common_shaft.polytropic_head_fluid_Joule_per_kg_values,
        ),
        outlet_pressure_bara_values,
    )

    for (
        expected_outlet_pressure,
        kappa,
        polytropic_efficiency,
        inlet_pressure_bara,
        molar_mass,
        z_inlet,
        inlet_temperature_K,
        polytropic_head_fluid_Joule_per_kg,
    ) in zip(
        outlet_pressure_bara_values,
        test_data_compressor_train_common_shaft.kappa_values,
        test_data_compressor_train_common_shaft.polytropic_efficiency_values,
        test_data_compressor_train_common_shaft.inlet_pressure_bara_values,
        test_data_compressor_train_common_shaft.molar_mass_values,
        test_data_compressor_train_common_shaft.z_inlet_values,
        test_data_compressor_train_common_shaft.inlet_temperature_K_values,
        test_data_compressor_train_common_shaft.polytropic_head_fluid_Joule_per_kg_values,
    ):
        assert calculate_outlet_pressure_campbell(
            kappa=kappa,
            inlet_pressure_bara=inlet_pressure_bara,
            inlet_temperature_K=inlet_temperature_K,
            molar_mass=molar_mass,
            z_inlet=z_inlet,
            polytropic_head_fluid_Joule_per_kg=polytropic_head_fluid_Joule_per_kg,
            polytropic_efficiency=polytropic_efficiency,
        ) == pytest.approx(expected_outlet_pressure)


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
