import numpy as np
import pandas as pd
import pytest

import libecalc.common.energy_usage_type
from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.units import Unit
from libecalc.domain.process.compressor.sampled import CompressorModelSampled
from libecalc.domain.process.compressor.sampled.compressor_model_sampled_1d import (
    CompressorModelSampled1D,
)
from libecalc.domain.process.compressor.sampled.compressor_model_sampled_2d import (
    CompressorModelSampled2DPsPd,
    CompressorModelSampled2DRatePd,
    CompressorModelSampled2DRatePs,
)
from libecalc.domain.process.compressor.sampled.compressor_model_sampled_3d import (
    CompressorModelSampled3D,
)
from libecalc.domain.process.core.results import TurbineResult


@pytest.fixture
def create_compressor_model_sampled():
    def _create(data: pd.DataFrame, energy_usage_type: EnergyUsageType | None = None) -> CompressorModelSampled:
        if energy_usage_type is None:
            energy_usage_type = EnergyUsageType.FUEL
        return CompressorModelSampled(
            energy_usage_values=data["FUEL"].tolist(),
            energy_usage_type=energy_usage_type,
            rate_values=data["RATE"].tolist() if "RATE" in data.columns else None,
            suction_pressure_values=data["PS"].tolist() if "PS" in data.columns else None,
            discharge_pressure_values=data["PD"].tolist() if "PD" in data.columns else None,
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
        rate=rate,
        suction_pressure=suction_pressure,
        discharge_pressure=discharge_pressure,
    )
    res = energy_func.evaluate().energy_usage
    np.testing.assert_allclose(res, expected)


def test_full_3d_compressor_degenerated_ps(create_compressor_model_sampled):
    data = pd.DataFrame(
        [
            [1000000, 50, 162, 52765],
            [1000000, 50, 258, 76928],
            [1000000, 50, 394, 118032],
            [1000000, 50, 471, 145965],
            [3000000, 50, 237, 71918],
            [3000000, 50, 258, 109823],
            [3000000, 50, 449, 137651],
            [7000000, 50, 322, 139839],
        ],
        columns=["RATE", "PS", "PD", "FUEL"],
    )
    energy_func = create_compressor_model_sampled(data=data)

    assert isinstance(energy_func._qhull_sampled, CompressorModelSampled2DRatePd)
    expected = [0, 0, 52765, 52765, np.nan]

    energy_func.set_evaluation_input(
        rate=np.asarray([-1, 0, 1e6, 1e6, 1e6]),
        suction_pressure=np.asarray([50, 50, 50, 52, 49]),
        discharge_pressure=np.asarray([162, 162, 162, 162, 162]),
    )
    res = energy_func.evaluate().energy_usage
    np.testing.assert_allclose(res, expected)


def test_full_3d_compressor_degenerated_rate(create_compressor_model_sampled):
    data = pd.DataFrame(
        [
            [1000000, 50, 162, 52765],
            [1000000, 50, 258, 76928],
            [1000000, 50, 394, 118032],
            [1000000, 50, 471, 145965],
            [1000000, 51, 166, 53000],
            [1000000, 51, 480, 148000],
            [1000000, 52, 171, 54441],
            [1000000, 52, 215, 65205],
            [1000000, 52, 336, 98692],
            [1000000, 52, 487, 151316],
        ],
        columns=["RATE", "PS", "PD", "FUEL"],
    )
    energy_func = create_compressor_model_sampled(data=data)

    assert isinstance(energy_func._qhull_sampled, CompressorModelSampled2DPsPd)

    expected = [0, 0, 52765, 54441, 54441, 131998.5, 52882.5, 52882.5, np.nan]

    energy_func.set_evaluation_input(
        rate=np.asarray([-1, 0, 1e6, 1e6, 1e6, 1e6, 1e6, 1e6 + 1e-15, 2e6]),
        suction_pressure=np.asarray([50, 50, 50, 52, 53, 50, 50.5, 50.5, 50]),
        discharge_pressure=np.asarray([162, 162, 162, 150, 150, 432.5, 162, 162, 162]),
    )
    res = energy_func.evaluate().energy_usage
    np.testing.assert_allclose(res, expected)


def test_full_3d_compressor_degenerated_pd(create_compressor_model_sampled):
    data = pd.DataFrame(
        [
            [1000000, 50, 300, 6.0],
            [3000000, 50, 300, 18.0],
            [7000000, 50, 300, 42.0],
            [1000000, 51, 300, 5.9],
            [1000000, 52, 300, 5.8],
            [3000000, 52, 300, 17.3],
            [7200000, 52, 300, 41.5],
        ],
        columns=["RATE", "PS", "PD", "FUEL"],
    )

    energy_func = create_compressor_model_sampled(data=data)

    assert isinstance(energy_func._qhull_sampled, CompressorModelSampled2DRatePs)
    expected = [0, 0, 6, 12, 5.95, np.nan]

    energy_func.set_evaluation_input(
        rate=np.asarray([-1, 0, 1e6, 2e6, 1e6, 1e6]),
        suction_pressure=np.asarray([50, 50, 50, 50, 50.5, 50]),
        discharge_pressure=np.asarray([162, 162, 300, 162, 300, 301]),
    )
    res = energy_func.evaluate().energy_usage
    np.testing.assert_allclose(res, expected)


def test_full_3d_compressor_degenerated_rate_ps(create_compressor_model_sampled):
    data = pd.DataFrame(
        [[1000000, 50, 162, 52765], [1000000, 50, 258, 76928], [1000000, 50, 394, 118032], [1000000, 50, 471, 145965]],
        columns=["RATE", "PS", "PD", "FUEL"],
    )

    energy_func = create_compressor_model_sampled(data=data)

    assert isinstance(energy_func._qhull_sampled, CompressorModelSampled1D)
    expected = [0, 0, 52765, 52765, np.nan]
    energy_func.set_evaluation_input(
        rate=np.asarray([-1, 0, 1e6, 1, 1e6]),
        suction_pressure=np.asarray([50, 50, 50, 50, 50]),
        discharge_pressure=np.asarray([162, 162, 162, 162, 472]),
    )
    res = energy_func.evaluate().energy_usage
    np.testing.assert_allclose(res, expected)


def test_2d_compressor_degenerated_ps(create_compressor_model_sampled):
    df_2d = pd.DataFrame(
        [
            [1000000, 162, 52765],
            [1000000, 258, 76928],
            [1000000, 394, 118032],
            [1000000, 471, 145965],
            [3000000, 237, 71918],
            [3000000, 258, 109823],
            [3000000, 449, 137651],
            [7000000, 322, 139839],
        ],
        columns=["RATE", "PD", "FUEL"],
    )

    energy_func = create_compressor_model_sampled(data=df_2d)

    assert isinstance(energy_func._qhull_sampled, CompressorModelSampled2DRatePd)

    expected = [0, 0, 52765, 52765, 52765]

    energy_func.set_evaluation_input(
        rate=np.asarray([-1, 0, 1e6, 1e6, 1e6]),
        suction_pressure=np.asarray([50, 50, 50, 52, 49]),
        discharge_pressure=np.asarray([162, 162, 162, 162, 162]),
    )
    res = energy_func.evaluate().energy_usage
    np.testing.assert_allclose(res, expected)


def test_2d_compressor_degenerated_rate(create_compressor_model_sampled):
    df_2d = pd.DataFrame(
        [
            [50, 162, 52765],
            [50, 258, 76928],
            [50, 394, 118032],
            [50, 471, 145965],
            [51, 166, 53000],
            [51, 480, 148000],
            [52, 171, 54441],
            [52, 215, 65205],
            [52, 336, 98692],
            [52, 487, 151316],
        ],
        columns=["PS", "PD", "FUEL"],
    )

    energy_func = create_compressor_model_sampled(data=df_2d)
    assert isinstance(energy_func._qhull_sampled, CompressorModelSampled2DPsPd)
    expected = [0, 0, 52765, 54441, 54441, 131998.5, 52882.5, 52882.5, 52765]

    energy_func.set_evaluation_input(
        rate=np.asarray([-1, 0, 1e6, 1e6, 1e6, 1e6, 1e6, 1e6 + 1e-15, 2e6]),
        suction_pressure=np.asarray([50, 50, 50, 52, 53, 50, 50.5, 50.5, 50]),
        discharge_pressure=np.asarray([162, 162, 162, 150, 150, 432.5, 162, 162, 162]),
    )
    res = energy_func.evaluate().energy_usage
    np.testing.assert_allclose(res, expected)


def test_2d_compressor_degenerated_pd():
    energy_func = CompressorModelSampled(
        energy_usage_values=[6.0, 18.0, 42.0, 5.9, 5.8, 17.3, 41.5],
        energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.FUEL,
        rate_values=[1000000, 3000000, 7000000, 1000000, 1000000, 3000000, 7200000],
        suction_pressure_values=[50, 50, 50, 51, 52, 52, 52],
        discharge_pressure_values=None,
        energy_usage_adjustment_constant=0.0,
        energy_usage_adjustment_factor=1.0,
    )
    assert isinstance(energy_func._qhull_sampled, CompressorModelSampled2DRatePs)
    expected = [0, 0, 6, 12, 5.95, 6]

    energy_func.set_evaluation_input(
        rate=np.asarray([-1, 0, 1e6, 2e6, 1e6, 1e6]),
        suction_pressure=np.asarray([50, 50, 50, 50, 50.5, 50]),
        discharge_pressure=np.asarray([162, 162, 300, 162, 300, 301]),
    )
    res = energy_func.evaluate().energy_usage
    np.testing.assert_allclose(res, expected)


def test_1d_compressor_rate():
    energy_func = CompressorModelSampled(
        energy_usage_values=[52765, 71918, 139839, 144574],
        energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.FUEL,
        rate_values=[1000000, 3000000, 7000000, 7200000],
        suction_pressure_values=None,
        discharge_pressure_values=None,
        energy_usage_adjustment_constant=0.0,
        energy_usage_adjustment_factor=1.0,
    )

    assert isinstance(energy_func._qhull_sampled, CompressorModelSampled1D)

    rate = np.asarray([-1, 0, 1e6, 7.2e6, 8e6])
    expected = [0, 0, 52765, 144574, np.nan]

    energy_func.set_evaluation_input(
        rate=np.asarray([-1, 0, 1e6, 7.2e6, 8e6]),
        suction_pressure=np.asarray([50, 50, 50, 53, 50]),
        discharge_pressure=np.asarray([162, 162, 150, 150, 432.5]),
    )
    res = energy_func.evaluate().energy_usage
    np.testing.assert_allclose(res, expected)
    energy_func.set_evaluation_input(rate=rate, suction_pressure=None, discharge_pressure=None)

    res = energy_func.evaluate().energy_usage
    np.testing.assert_allclose(res, expected)


def test_1d_compressor_pd():
    energy_func = CompressorModelSampled(
        energy_usage_values=[52765, 71918, 139839, 144574],
        energy_usage_type=libecalc.common.energy_usage_type.EnergyUsageType.FUEL,
        rate_values=None,
        suction_pressure_values=None,
        discharge_pressure_values=[1000000, 3000000, 7000000, 7200000],
        energy_usage_adjustment_constant=0.0,
        energy_usage_adjustment_factor=1.0,
    )

    assert isinstance(energy_func._qhull_sampled, CompressorModelSampled1D)

    pr_d = np.asarray([-1, 0, 1e6, 7.2e6, 8e6])
    expected = [52765, 52765, 52765, 144574, np.nan]

    energy_func.set_evaluation_input(
        rate=None,
        suction_pressure=None,
        discharge_pressure=pr_d,
    )
    res = energy_func.evaluate().energy_usage
    energy_func.set_evaluation_input(rate=None, suction_pressure=None, discharge_pressure=pr_d)
    np.testing.assert_allclose(res, expected)
    res = energy_func.evaluate().energy_usage
    np.testing.assert_allclose(res, expected)
    energy_func.set_evaluation_input(rate=None, suction_pressure=pr_d, discharge_pressure=pr_d)
    res = energy_func.evaluate().energy_usage
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
        fuel_rate=fuel_usage_values,
        efficiency=list(np.ones_like(fuel_usage_values)),
        load=[0, 0, 2, 3, 16, np.nan, np.nan],
        energy_usage=fuel_usage_values,
        energy_usage_unit=Unit.STANDARD_CUBIC_METER_PER_DAY,
        power=[0, 0, 2, 3, 16, np.nan, np.nan],
        power_unit=Unit.MEGA_WATT,
        exceeds_maximum_load=[False, False, False, False, True, True],
    )
    turbine_result = turbine.calculate_turbine_power_usage(np.asarray(fuel_usage_values))

    assert np.array_equal(turbine_result.fuel_rate, expected_turbine_result.fuel_rate)
    assert np.array_equal(turbine_result.efficiency, expected_turbine_result.efficiency)
    assert np.array_equal(turbine_result.load, expected_turbine_result.load, equal_nan=True)
