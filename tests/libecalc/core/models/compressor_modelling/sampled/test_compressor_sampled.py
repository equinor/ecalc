from itertools import combinations, product

import numpy as np
import pandas as pd
import pytest

import libecalc.common.energy_usage_type
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.units import Unit
from libecalc.domain.component_validation_error import CompressorModelSampledEvaluationInputValidationException
from libecalc.domain.process.compressor.core.sampled import CompressorModelSampled
from libecalc.domain.process.compressor.core.sampled.compressor_model_sampled_1d import (
    CompressorModelSampled1D,
)
from libecalc.domain.process.compressor.core.sampled.compressor_model_sampled_2d import (
    CompressorModelSampled2DPsPd,
    CompressorModelSampled2DRatePd,
    CompressorModelSampled2DRatePs,
)
from libecalc.domain.process.compressor.core.sampled.compressor_model_sampled_3d import (
    CompressorModelSampled3D,
)
from libecalc.domain.process.compressor.core.sampled.constants import RATE_NAME, PS_NAME, PD_NAME
from libecalc.domain.process.core.results import TurbineResult


@pytest.fixture
def create_compressor_model_sampled():
    def _create(data: dict, energy_usage_type: EnergyUsageType | None = None) -> CompressorModelSampled:
        if energy_usage_type is None:
            energy_usage_type = EnergyUsageType.FUEL
        return CompressorModelSampled(
            energy_usage_values=data.get("FUEL"),
            energy_usage_type=energy_usage_type,
            rate_values=data.get("RATE"),
            suction_pressure_values=data.get("PS"),
            discharge_pressure_values=data.get("PD"),
            energy_usage_adjustment_constant=0.0,
            energy_usage_adjustment_factor=1.0,
        )

    return _create


def test_full_3d_compressor():
    energy_func = CompressorModelSampled(
        energy_usage_values=[
            52765,
            76928,
            118032,
            145965,
            71918,
            109823,
            137651,
            139839,
            53000,
            148000,
            54441,
            65205,
            98692,
            151316,
            74603,
            114277,
            143135,
            144574,
        ],
        rate_values=list(
            1000000
            * np.asarray([1.0, 1.0, 1.0, 1.0, 3.0, 3.0, 3.0, 7.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 3.0, 3.0, 3.0, 7.2])
        ),
        suction_pressure_values=list(
            np.asarray([50, 50, 50, 50, 50, 50, 50, 50, 51, 51, 52, 52, 52, 52, 52, 52, 52, 52])
        ),
        discharge_pressure_values=list(
            np.asarray([162, 258, 394, 471, 237, 258, 449, 322, 166, 480, 171, 215, 336, 487, 249, 384, 466, 362])
        ),
        energy_usage_adjustment_constant=0.0,
        energy_usage_adjustment_factor=1.0,
        energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.FUEL,
    )

    assert isinstance(energy_func._qhull_sampled, CompressorModelSampled3D)

    # Test
    # - normal evaluation
    # - zero and negative rate
    # - regularity
    # - non-robust rate wrt numerical errors
    rate = np.asarray([-1, 0, 1e6, 1e6, 1e6, 1e6, 1e6, 2e6, 7.2e6 + 1e-15])
    suction_pressure = np.asarray([50, 50, 50, 52, 53, 50, 50.5, 50, 52])
    discharge_pressure = np.asarray([162, 162, 162, 150, 150, 432.5, 162, 162, 362])
    expected = [
        0,
        0,
        52765,
        54441,
        54441,
        131998.5,
        52882.5,
        67277.33,
        144574,
    ]

    energy_func.set_evaluation_input(
        rate=rate, suction_pressure=suction_pressure, discharge_pressure=discharge_pressure
    )
    res = energy_func.evaluate().get_energy_result().energy_usage.values
    np.testing.assert_allclose(res, expected)


def test_full_3d_compressor_degenerated_ps(create_compressor_model_sampled):
    data = {
        "RATE": [1000000, 1000000, 1000000, 1000000, 3000000, 3000000, 3000000, 7000000],
        "PS": [50, 50, 50, 50, 50, 50, 50, 50],
        "PD": [162, 258, 394, 471, 237, 258, 449, 322],
        "FUEL": [52765, 76928, 118032, 145965, 71918, 109823, 137651, 139839],
    }
    energy_func = create_compressor_model_sampled(data=data)

    assert isinstance(energy_func._qhull_sampled, CompressorModelSampled2DRatePd)
    expected = [0, 0, 52765, 52765, np.nan]

    energy_func.set_evaluation_input(
        rate=np.asarray([-1, 0, 1e6, 1e6, 1e6]),
        suction_pressure=np.asarray([50, 50, 50, 52, 49]),
        discharge_pressure=np.asarray([162, 162, 162, 162, 162]),
    )
    res = energy_func.evaluate().get_energy_result().energy_usage.values
    np.testing.assert_allclose(res, expected)


def test_full_3d_compressor_degenerated_rate(create_compressor_model_sampled):
    data = {
        "RATE": [1000000] * 10,
        "PS": [50, 50, 50, 50, 51, 51, 52, 52, 52, 52],
        "PD": [162, 258, 394, 471, 166, 480, 171, 215, 336, 487],
        "FUEL": [52765, 76928, 118032, 145965, 53000, 148000, 54441, 65205, 98692, 151316],
    }
    energy_func = create_compressor_model_sampled(data=data)

    assert isinstance(energy_func._qhull_sampled, CompressorModelSampled2DPsPd)

    expected = [0, 0, 52765, 54441, 54441, 131998.5, 52882.5, 52882.5, np.nan]

    energy_func.set_evaluation_input(
        rate=np.asarray([-1, 0, 1e6, 1e6, 1e6, 1e6, 1e6, 1e6 + 1e-15, 2e6]),
        suction_pressure=np.asarray([50, 50, 50, 52, 53, 50, 50.5, 50.5, 50]),
        discharge_pressure=np.asarray([162, 162, 162, 150, 150, 432.5, 162, 162, 162]),
    )
    res = energy_func.evaluate().get_energy_result().energy_usage.values
    np.testing.assert_allclose(res, expected)


def test_full_3d_compressor_degenerated_pd(create_compressor_model_sampled):
    data = {
        "RATE": [1000000, 3000000, 7000000, 1000000, 1000000, 3000000, 7200000],
        "PS": [50, 50, 50, 51, 52, 52, 52],
        "PD": [300, 300, 300, 300, 300, 300, 300],
        "FUEL": [6.0, 18.0, 42.0, 5.9, 5.8, 17.3, 41.5],
    }

    energy_func = create_compressor_model_sampled(data=data)

    assert isinstance(energy_func._qhull_sampled, CompressorModelSampled2DRatePs)
    expected = [0, 0, 6, 12, 5.95, np.nan]

    energy_func.set_evaluation_input(
        rate=np.asarray([-1, 0, 1e6, 2e6, 1e6, 1e6]),
        suction_pressure=np.asarray([50, 50, 50, 50, 50.5, 50]),
        discharge_pressure=np.asarray([162, 162, 300, 162, 300, 301]),
    )
    res = energy_func.evaluate().get_energy_result().energy_usage.values
    np.testing.assert_allclose(res, expected)


def test_full_3d_compressor_degenerated_rate_ps(create_compressor_model_sampled):
    data = {
        "RATE": [1000000, 1000000, 1000000, 1000000],
        "PS": [50, 50, 50, 50],
        "PD": [162, 258, 394, 471],
        "FUEL": [52765, 76928, 118032, 145965],
    }

    energy_func = create_compressor_model_sampled(data=data)

    assert isinstance(energy_func._qhull_sampled, CompressorModelSampled1D)
    expected = [0, 0, 52765, 52765, np.nan]
    energy_func.set_evaluation_input(
        rate=np.asarray([-1, 0, 1e6, 1, 1e6]),
        suction_pressure=np.asarray([50, 50, 50, 50, 50]),
        discharge_pressure=np.asarray([162, 162, 162, 162, 472]),
    )
    res = energy_func.evaluate().get_energy_result().energy_usage.values
    np.testing.assert_allclose(res, expected)


def test_2d_compressor_degenerated_ps(create_compressor_model_sampled):
    data = {
        "RATE": [1000000, 1000000, 1000000, 1000000, 3000000, 3000000, 3000000, 7000000],
        "PD": [162, 258, 394, 471, 237, 258, 449, 322],
        "FUEL": [52765, 76928, 118032, 145965, 71918, 109823, 137651, 139839],
    }

    energy_func = create_compressor_model_sampled(data=data)

    assert isinstance(energy_func._qhull_sampled, CompressorModelSampled2DRatePd)

    expected = [0, 0, 52765, 52765, 52765]

    energy_func.set_evaluation_input(
        rate=np.asarray([-1, 0, 1e6, 1e6, 1e6]),
        suction_pressure=np.asarray([50, 50, 50, 52, 49]),
        discharge_pressure=np.asarray([162, 162, 162, 162, 162]),
    )
    res = energy_func.evaluate().get_energy_result().energy_usage.values
    np.testing.assert_allclose(res, expected)


def test_2d_compressor_degenerated_rate(create_compressor_model_sampled):
    data = {
        "PS": [50, 50, 50, 50, 51, 51, 52, 52, 52, 52],
        "PD": [162, 258, 394, 471, 166, 480, 171, 215, 336, 487],
        "FUEL": [52765, 76928, 118032, 145965, 53000, 148000, 54441, 65205, 98692, 151316],
    }

    energy_func = create_compressor_model_sampled(data=data)
    assert isinstance(energy_func._qhull_sampled, CompressorModelSampled2DPsPd)
    expected = [0, 0, 52765, 54441, 54441, 131998.5, 52882.5, 52882.5, 52765]

    energy_func.set_evaluation_input(
        rate=np.asarray([-1, 0, 1e6, 1e6, 1e6, 1e6, 1e6, 1e6 + 1e-15, 2e6]),
        suction_pressure=np.asarray([50, 50, 50, 52, 53, 50, 50.5, 50.5, 50]),
        discharge_pressure=np.asarray([162, 162, 162, 150, 150, 432.5, 162, 162, 162]),
    )
    res = energy_func.evaluate().get_energy_result().energy_usage.values
    np.testing.assert_allclose(res, expected)


def test_2d_compressor_degenerated_pd(create_compressor_model_sampled):
    data = {
        "RATE": [1000000, 3000000, 7000000, 1000000, 1000000, 3000000, 7200000],
        "PS": [50, 50, 50, 51, 52, 52, 52],
        "FUEL": [6.0, 18.0, 42.0, 5.9, 5.8, 17.3, 41.5],
    }
    energy_func = create_compressor_model_sampled(data=data)
    assert isinstance(energy_func._qhull_sampled, CompressorModelSampled2DRatePs)
    expected = [0, 0, 6, 12, 5.95, 6]

    energy_func.set_evaluation_input(
        rate=np.asarray([-1, 0, 1e6, 2e6, 1e6, 1e6]),
        suction_pressure=np.asarray([50, 50, 50, 50, 50.5, 50]),
        discharge_pressure=np.asarray([162, 162, 300, 162, 300, 301]),
    )
    res = energy_func.evaluate().get_energy_result().energy_usage.values
    np.testing.assert_allclose(res, expected)


def test_1d_compressor_rate(create_compressor_model_sampled):
    data = {
        "RATE": [1000000, 3000000, 7000000, 7200000],
        "FUEL": [52765, 71918, 139839, 144574],
    }
    energy_func = create_compressor_model_sampled(data=data)
    assert isinstance(energy_func._qhull_sampled, CompressorModelSampled1D)

    rate = np.asarray([-1, 0, 1e6, 7.2e6, 8e6])
    expected = [0, 0, 52765, 144574, np.nan]

    energy_func.set_evaluation_input(
        rate=np.asarray([-1, 0, 1e6, 7.2e6, 8e6]),
        suction_pressure=np.asarray([50, 50, 50, 53, 50]),
        discharge_pressure=np.asarray([162, 162, 150, 150, 432.5]),
    )
    res = energy_func.evaluate().get_energy_result().energy_usage.values
    np.testing.assert_allclose(res, expected)
    energy_func.set_evaluation_input(rate=rate, suction_pressure=None, discharge_pressure=None)

    res = energy_func.evaluate().get_energy_result().energy_usage.values
    np.testing.assert_allclose(res, expected)


def test_1d_compressor_pd(create_compressor_model_sampled):
    data = {
        "PD": [1000000, 3000000, 7000000, 7200000],
        "FUEL": [52765, 71918, 139839, 144574],
    }
    energy_func = create_compressor_model_sampled(data=data)

    assert isinstance(energy_func._qhull_sampled, CompressorModelSampled1D)

    pr_d = np.asarray([-1, 0, 1e6, 7.2e6, 8e6])
    expected = [52765, 52765, 52765, 144574, np.nan]

    energy_func.set_evaluation_input(rate=None, suction_pressure=None, discharge_pressure=pr_d)
    res = energy_func.evaluate().get_energy_result().energy_usage.values
    np.testing.assert_allclose(res, expected)

    energy_func.set_evaluation_input(rate=None, suction_pressure=pr_d, discharge_pressure=pr_d)
    res = energy_func.evaluate().get_energy_result().energy_usage.values
    np.testing.assert_allclose(res, expected)


def test_turbine_with_no_data():
    turbine = CompressorModelSampled.Turbine(None, None)
    assert turbine.fuel_to_power_function is None
    assert turbine.calculate_turbine_power_usage(None) is None
    assert turbine.calculate_turbine_power_usage(np.array([1])) is None


def test_turbine_with_different_lengths():
    turbine = CompressorModelSampled.Turbine(np.array([1, 2]), np.array([1]))
    assert turbine.fuel_to_power_function is None
    assert turbine.calculate_turbine_power_usage(None) is None
    assert turbine.calculate_turbine_power_usage(np.array([1])) is None


def test_turbine_with_actual_data():
    turbine = CompressorModelSampled.Turbine(np.array([1, 2, 3, 4]), np.array([2, 4, 8, 16]))
    assert turbine.fuel_to_power_function is not None

    fuel_usage_values = [-1, 0, 1, 1.5, 4, 4.5, 6]
    expected_turbine_result = TurbineResult(
        efficiency=list(np.ones_like(fuel_usage_values)),
        load=[0, 0, 2, 3, 16, np.nan, np.nan],
        load_unit=Unit.MEGA_WATT,
        energy_usage=fuel_usage_values,
        energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
        exceeds_maximum_load=[False, False, False, False, True, True],
    )
    turbine_result = turbine.calculate_turbine_power_usage(np.asarray(fuel_usage_values))

    expected_energy_result = expected_turbine_result.get_energy_result()
    energy_result = turbine_result.get_energy_result()
    assert np.array_equal(energy_result.energy_usage.values, expected_energy_result.energy_usage.values)
    assert np.array_equal(turbine_result.efficiency, expected_turbine_result.efficiency)
    assert np.array_equal(energy_result.power.values, expected_energy_result.power.values, equal_nan=True)


def test_required_evaluation_input_1d_rate(create_compressor_model_sampled):
    """
    Model built with only rate. Rate is required as evaluation input.
    Missing it should raise a validation exception.
    """
    data = {"FUEL": [60000, 80000, 100000], "RATE": [2, 4, 6]}
    model = create_compressor_model_sampled(data=data)

    # Valid: rate provided
    model.set_evaluation_input(rate=np.array([3]), suction_pressure=None, discharge_pressure=None)
    model.evaluate()

    # Invalid: rate not provided
    with pytest.raises(CompressorModelSampledEvaluationInputValidationException):
        model.set_evaluation_input(rate=None, suction_pressure=np.array([15]), discharge_pressure=None)


def test_required_evaluation_input_1d_suction(create_compressor_model_sampled):
    """
    Model built with only suction pressure. Suction pressure is required as evaluation input.
    Missing it should raise a validation exception.
    """
    data = {"FUEL": [60000, 80000, 100000], "PS": [10, 20, 30]}
    model = create_compressor_model_sampled(data=data)

    # Valid: suction pressure provided
    model.set_evaluation_input(rate=None, suction_pressure=np.array([15]), discharge_pressure=None)
    model.evaluate()

    # Invalid: suction pressure not provided
    with pytest.raises(CompressorModelSampledEvaluationInputValidationException):
        model.set_evaluation_input(rate=np.array([3]), suction_pressure=None, discharge_pressure=None)


def test_required_evaluation_input_1d_discharge(create_compressor_model_sampled):
    """
    Model built with only discharge pressure. Discharge pressure is required as evaluation input.
    Missing it should raise a validation exception.
    """
    data = {"FUEL": [60000, 80000, 100000], "PD": [100, 200, 300]}
    model = create_compressor_model_sampled(data=data)

    # Valid: discharge pressure provided
    model.set_evaluation_input(rate=None, suction_pressure=None, discharge_pressure=np.array([150]))
    model.evaluate()

    # Invalid: discharge pressure not provided
    with pytest.raises(CompressorModelSampledEvaluationInputValidationException):
        model.set_evaluation_input(rate=np.array([3]), suction_pressure=None, discharge_pressure=None)


def test_required_evaluation_input_2d_rate_suction(create_compressor_model_sampled):
    """
    Model built with rate and suction pressure. Both are required as evaluation input.
    Missing any of them should raise a validation exception.
    """
    data = {
        "FUEL": [60000, 80000, 100000, 120000],
        "RATE": [2, 2, 4, 4],
        "PS": [10, 20, 10, 20],
    }
    model = create_compressor_model_sampled(data=data)

    # Valid: both rate and suction pressure provided
    model.set_evaluation_input(rate=np.array([3]), suction_pressure=np.array([15]), discharge_pressure=None)
    model.evaluate()

    # Invalid: missing either rate or suction pressure or both
    with pytest.raises(CompressorModelSampledEvaluationInputValidationException):
        model.set_evaluation_input(rate=None, suction_pressure=np.array([15]), discharge_pressure=None)


def test_required_evaluation_input_2d_rate_discharge(create_compressor_model_sampled):
    """
    Model built with rate and discharge pressure. Both are required as evaluation input.
    Missing any of them should raise a validation exception.
    """
    data = {
        "FUEL": [60000, 80000, 100000, 120000],
        "RATE": [2, 2, 4, 4],
        "PD": [100, 200, 100, 200],
    }
    model = create_compressor_model_sampled(data=data)

    # Valid: both rate and discharge pressure provided
    model.set_evaluation_input(rate=np.array([3]), suction_pressure=None, discharge_pressure=np.array([150]))
    model.evaluate()

    # Invalid: missing either rate or discharge pressure or both
    with pytest.raises(CompressorModelSampledEvaluationInputValidationException):
        model.set_evaluation_input(rate=None, suction_pressure=None, discharge_pressure=np.array([150]))


def test_required_evaluation_input_2d_suction_discharge(create_compressor_model_sampled):
    """
    Model built with suction pressure and discharge pressure. Both are required as evaluation input.
    Missing any of them should raise a validation exception.
    """
    data = {
        "FUEL": [60000, 80000, 100000, 120000],
        "PS": [10, 10, 20, 20],
        "PD": [100, 200, 100, 200],
    }
    model = create_compressor_model_sampled(data=data)

    # Valid: both suction and discharge pressure provided
    model.set_evaluation_input(rate=None, suction_pressure=np.array([15]), discharge_pressure=np.array([150]))
    model.evaluate()

    # Invalid: missing either suction or discharge pressure or both
    with pytest.raises(CompressorModelSampledEvaluationInputValidationException):
        model.set_evaluation_input(rate=None, suction_pressure=None, discharge_pressure=np.array([1500]))


def test_required_evaluation_input_3d(create_compressor_model_sampled):
    """
    Model built with rate, suction pressure, and discharge pressure. All three are required
    as evaluation input. Missing any of them should raise a validation exception.
    """
    data = {
        "FUEL": [60000, 80000, 100000, 120000],
        "RATE": [2, 2, 4, 4],
        "PS": [10, 10, 10, 10],
        "PD": [100, 200, 300, 400],
    }
    model = create_compressor_model_sampled(data=data)

    # Valid: rate, suction and discharge pressure provided
    model.set_evaluation_input(rate=np.array([3]), suction_pressure=np.array([15]), discharge_pressure=np.array([150]))
    model.evaluate()

    # Invalid: missing any of the three inputs
    with pytest.raises(CompressorModelSampledEvaluationInputValidationException):
        model.set_evaluation_input(rate=np.array([3]), suction_pressure=None, discharge_pressure=np.array([150]))
