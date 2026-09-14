import math

import numpy as np
import pandas as pd
import pytest

from libecalc.common.energy_usage_type import EnergyUsageType
from libecalc.common.errors.ecalc_validation_error import (
    ProcessEqualLengthValidationException,
    ProcessMissingVariableValidationException,
    ProcessNegativeValuesValidationException,
)
from libecalc.common.errors.exceptions import IllegalStateException, InvalidColumnException
from libecalc.domain.process.compressor.core.sampled.compressor_model_sampled import (
    CompressorModelSampled as LegacyCompressorModelSampled,
)
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
from libecalc.energy.models.sampled_compressor import (
    EPSILON,
    PD_NAME,
    PS_NAME,
    RATE_NAME,
    SampledCompressor,
    SampledCompressor1D,
    SampledCompressor2D,
    SampledCompressor3D,
)

LEGACY_2D_MODELS = {
    (RATE_NAME, PD_NAME): CompressorModelSampled2DRatePd,
    (RATE_NAME, PS_NAME): CompressorModelSampled2DRatePs,
    (PS_NAME, PD_NAME): CompressorModelSampled2DPsPd,
}


def _assert_allclose(actual, expected) -> None:
    np.testing.assert_allclose(actual, expected, rtol=1e-9, atol=1e-9, equal_nan=True)


def _legacy_model(data: dict[str, list[float]]) -> LegacyCompressorModelSampled:
    return LegacyCompressorModelSampled(
        energy_usage_type=EnergyUsageType.FUEL,
        energy_usage_values=data["energy_usage_values"],
        rate_values=data.get("rate_values"),
        suction_pressure_values=data.get("suction_pressure_values"),
        discharge_pressure_values=data.get("discharge_pressure_values"),
        power_interpolation_values=data.get("power_interpolation_values"),
    )


def _scalar_evaluation_cases(evaluation: dict[str, list[float]]) -> list[dict[str, float]]:
    return [
        {
            "rate": rate,
            "suction_pressure": suction_pressure,
            "discharge_pressure": discharge_pressure,
        }
        for rate, suction_pressure, discharge_pressure in zip(
            evaluation["rate"],
            evaluation["suction_pressure"],
            evaluation["discharge_pressure"],
            strict=True,
        )
    ]


def _legacy_direct_evaluate(model, rate=None, suction_pressure=None, discharge_pressure=None) -> float:
    return float(
        np.asarray(
            model.evaluate(
                rate=None if rate is None else np.asarray([rate], dtype=np.float64),
                suction_pressure=None if suction_pressure is None else np.asarray([suction_pressure], dtype=np.float64),
                discharge_pressure=(
                    None if discharge_pressure is None else np.asarray([discharge_pressure], dtype=np.float64)
                ),
            ),
            dtype=np.float64,
        )[0]
    )


def _legacy_evaluate(data: dict[str, list[float]], rate, suction_pressure, discharge_pressure) -> float:
    model = _legacy_model(data)
    model.set_evaluation_input(
        rate=None if rate is None else np.asarray([rate], dtype=np.float64),
        fluid_model=None,
        suction_pressure=None if suction_pressure is None else np.asarray([suction_pressure], dtype=np.float64),
        discharge_pressure=None if discharge_pressure is None else np.asarray([discharge_pressure], dtype=np.float64),
    )
    return float(np.asarray(model.evaluate().get_energy_result().energy_usage.values, dtype=np.float64)[0])


def _legacy_max_rate(data: dict[str, list[float]], suction_pressure=None, discharge_pressure=None) -> float:
    model = _legacy_model(data)
    result = model.get_max_standard_rate(
        suction_pressures=None if suction_pressure is None else np.asarray([suction_pressure], dtype=np.float64),
        discharge_pressures=None if discharge_pressure is None else np.asarray([discharge_pressure], dtype=np.float64),
    )
    assert result is not None
    return float(np.asarray(result, dtype=np.float64)[0])


def _legacy_2d_max_rate(model, variables, suction_pressure=None, discharge_pressure=None) -> float:
    if variables == (RATE_NAME, PD_NAME):
        return float(
            np.asarray(model.get_max_rate(discharge_pressure=np.asarray([discharge_pressure], dtype=np.float64)))[0]
        )
    return float(np.asarray(model.get_max_rate(np.asarray([suction_pressure], dtype=np.float64)))[0])


def _legacy_3d_project(legacy, rate, suction_pressure, discharge_pressure) -> tuple[float, float, float]:
    projected = legacy._project_variables_for_evaluation(
        rate=np.asarray([rate], dtype=np.float64),
        suction_pressure=np.asarray([suction_pressure], dtype=np.float64),
        discharge_pressure=np.asarray([discharge_pressure], dtype=np.float64),
    )
    return float(projected[0][0]), float(projected[1][0]), float(projected[2][0])


def _legacy_3d_max_rate(model, suction_pressure, discharge_pressure) -> float:
    return float(
        np.asarray(
            model.get_max_rate(
                ps=np.asarray([suction_pressure], dtype=np.float64),
                pd=np.asarray([discharge_pressure], dtype=np.float64),
            ),
            dtype=np.float64,
        )[0]
    )


@pytest.mark.parametrize(
    ("data", "evaluation", "active_variables"),
    [
        (
            {
                "energy_usage_values": [
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
                "rate_values": (
                    1_000_000
                    * np.asarray(
                        [1.0, 1.0, 1.0, 1.0, 3.0, 3.0, 3.0, 7.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 3.0, 3.0, 3.0, 7.2]
                    )
                ).tolist(),
                "suction_pressure_values": np.asarray(
                    [50, 50, 50, 50, 50, 50, 50, 50, 51, 51, 52, 52, 52, 52, 52, 52, 52, 52]
                ).tolist(),
                "discharge_pressure_values": np.asarray(
                    [162, 258, 394, 471, 237, 258, 449, 322, 166, 480, 171, 215, 336, 487, 249, 384, 466, 362]
                ).tolist(),
            },
            {
                "rate": [-1, 0, 1e6, 1e6, 1e6, 1e6, 1e6, 2e6, 7.2e6 + 1e-15],
                "suction_pressure": [50, 50, 50, 52, 53, 50, 50.5, 50, 52],
                "discharge_pressure": [162, 162, 162, 150, 150, 432.5, 162, 162, 362],
            },
            (RATE_NAME, PS_NAME, PD_NAME),
        ),
        (
            {
                "energy_usage_values": [52765, 76928, 118032, 145965, 71918, 109823, 137651, 139839],
                "rate_values": [1e6, 1e6, 1e6, 1e6, 3e6, 3e6, 3e6, 7e6],
                "suction_pressure_values": [50] * 8,
                "discharge_pressure_values": [162, 258, 394, 471, 237, 258, 449, 322],
            },
            {
                "rate": [-1, 0, 1e6, 1e6, 1e6],
                "suction_pressure": [50, 50, 50, 52, 49],
                "discharge_pressure": [162, 162, 162, 162, 162],
            },
            (RATE_NAME, PD_NAME),
        ),
        (
            {
                "energy_usage_values": [52765, 76928, 118032, 145965, 53000, 148000, 54441, 65205, 98692, 151316],
                "rate_values": [1e6] * 10,
                "suction_pressure_values": [50, 50, 50, 50, 51, 51, 52, 52, 52, 52],
                "discharge_pressure_values": [162, 258, 394, 471, 166, 480, 171, 215, 336, 487],
            },
            {
                "rate": [-1, 0, 1e6, 1e6, 1e6, 1e6, 1e6, 1e6 + 1e-15, 2e6],
                "suction_pressure": [50, 50, 50, 52, 53, 50, 50.5, 50.5, 50],
                "discharge_pressure": [162, 162, 162, 150, 150, 432.5, 162, 162, 162],
            },
            (PS_NAME, PD_NAME),
        ),
        (
            {
                "energy_usage_values": [6.0, 18.0, 42.0, 5.9, 5.8, 17.3, 41.5],
                "rate_values": [1e6, 3e6, 7e6, 1e6, 1e6, 3e6, 7.2e6],
                "suction_pressure_values": [50, 50, 50, 51, 52, 52, 52],
                "discharge_pressure_values": [300] * 7,
            },
            {
                "rate": [-1, 0, 1e6, 2e6, 1e6, 1e6],
                "suction_pressure": [50, 50, 50, 50, 50.5, 50],
                "discharge_pressure": [162, 162, 300, 162, 300, 301],
            },
            (RATE_NAME, PS_NAME),
        ),
        (
            {
                "energy_usage_values": [52765, 76928, 118032, 145965],
                "rate_values": [1e6] * 4,
                "suction_pressure_values": [50] * 4,
                "discharge_pressure_values": [162, 258, 394, 471],
            },
            {
                "rate": [-1, 0, 1e6, 1, 1e6],
                "suction_pressure": [50, 50, 50, 50, 50],
                "discharge_pressure": [162, 162, 162, 162, 472],
            },
            (PD_NAME,),
        ),
        (
            {
                "energy_usage_values": [52765, 71918, 139839, 144574],
                "rate_values": [1e6, 3e6, 7e6, 7.2e6],
            },
            {
                "rate": [-1, 0, 1e6, 7.2e6, 8e6, EPSILON / 2],
                "suction_pressure": [50, 50, 50, 53, 50, 50],
                "discharge_pressure": [162, 162, 150, 150, 432.5, 162],
            },
            (RATE_NAME,),
        ),
        (
            {
                "energy_usage_values": [2.0, 3.0, 4.0],
                "suction_pressure_values": [2.0, 3.0, 4.0],
            },
            {
                "rate": [1.0, 1.0, 1.0, 1.0],
                "suction_pressure": [1.0, 2.0, 4.0, 5.0],
                "discharge_pressure": [1.0, 1.0, 1.0, 1.0],
            },
            (PS_NAME,),
        ),
    ],
)
def test_dispatcher_matches_legacy(data, evaluation, active_variables):
    common = SampledCompressor(**data)

    assert common.active_variables == active_variables
    for query in _scalar_evaluation_cases(evaluation):
        common_result = common.evaluate(**query)
        legacy_result = _legacy_evaluate(data, **query)
        _assert_allclose(common_result.energy_usage, legacy_result)


@pytest.mark.parametrize(
    ("x_name", "sampled_data", "test_data"),
    [
        (RATE_NAME, [[3, 3], [2, 2], [4, 4]], [1, 2, 3, 4, 5]),
        (PS_NAME, [[3, 3], [2, 4], [4, 2]], [1, 2, 3, 4, 5]),
        (PD_NAME, [[3, 3], [2, 2], [4, 4]], [1, 2, 3, 4, 5]),
    ],
)
def test_1d_direct_matches_legacy(x_name, sampled_data, test_data):
    frame = pd.DataFrame(sampled_data, columns=[x_name, "ENERGY"])
    legacy = CompressorModelSampled1D(frame, "ENERGY")
    common = SampledCompressor1D(
        x_name, frame[x_name].to_numpy(dtype=np.float64), frame["ENERGY"].to_numpy(dtype=np.float64)
    )
    argument_name = {
        RATE_NAME: "rate",
        PS_NAME: "suction_pressure",
        PD_NAME: "discharge_pressure",
    }[x_name]
    for value in test_data:
        kwargs = {argument_name: value}
        _assert_allclose(common.evaluate(**kwargs), _legacy_direct_evaluate(legacy, **kwargs))
    assert common.get_max_rate() == legacy.get_max_rate()


@pytest.mark.parametrize(
    ("variables", "rows", "rate", "suction_pressure", "discharge_pressure"),
    [
        (
            (RATE_NAME, PD_NAME),
            [
                [8, 5, 5],
                [3, 1, 5],
                [1, 4, 5],
                [2, 2, 5],
                [2, 6, 5],
                [3, 7, 5],
                [4, 8, 5],
                [7, 6, 5],
                [7, 3, 5],
                [5, 2, 5],
                [4, 4, 1],
            ],
            [4, 2.5, 5, 2, 1, 6, 7, 2, 2, 9, 9],
            [0] * 11,
            [4, 4, 9, 7, 2, 1, 7, 10, 0, 1, 9],
        ),
        (
            (RATE_NAME, PS_NAME),
            [
                [3, 1, 5],
                [1, 4, 5],
                [2, 2, 5],
                [2, 6, 5],
                [3, 7, 5],
                [4, 8, 5],
                [7, 6, 5],
                [8, 5, 5],
                [7, 3, 5],
                [5, 2, 5],
                [4, 4, 1],
            ],
            [4, 2.5, 5.5, 9, 6, 0, 1, 0, 1],
            [4, 4, 9, 4, 2, 0, 1.5, 6, 9],
            [0] * 9,
        ),
        (
            (PS_NAME, PD_NAME),
            [
                [1, 3, 5],
                [2, 2, 5],
                [4, 1, 5],
                [6, 2, 5],
                [7, 3, 5],
                [8, 4, 5],
                [6, 7, 5],
                [5, 8, 5],
                [3, 7, 5],
                [2, 5, 5],
                [4, 4, 1],
            ],
            [0] * 11,
            [4, 5, 9, 6, 0, 1, 0, 1, 4, 9, 9],
            [4, 9, 4, 2, 0, 1.5, 6, 9, 2.5, 2, 5],
        ),
    ],
)
def test_2d_direct_matches_legacy(variables, rows, rate, suction_pressure, discharge_pressure):
    frame = pd.DataFrame(rows, columns=[*variables, "ENERGY"])
    legacy = LEGACY_2D_MODELS[variables](frame, "ENERGY")
    common = SampledCompressor2D(
        variables, frame[list(variables)].to_numpy(dtype=np.float64), frame["ENERGY"].to_numpy(dtype=np.float64)
    )

    for query in _scalar_evaluation_cases(
        {
            "rate": rate,
            "suction_pressure": suction_pressure,
            "discharge_pressure": discharge_pressure,
        }
    ):
        _assert_allclose(common.evaluate(**query), _legacy_direct_evaluate(legacy, **query))

    if variables == (RATE_NAME, PD_NAME):
        for discharge_value in [0, 2, 4, 6, 8, 9]:
            _assert_allclose(
                common.get_max_rate(discharge_pressure=discharge_value),
                _legacy_2d_max_rate(legacy, variables, discharge_pressure=discharge_value),
            )
    if variables == (RATE_NAME, PS_NAME):
        for suction_value in [0, 2, 4, 6, 9]:
            _assert_allclose(
                common.get_max_rate(suction_pressure=suction_value),
                _legacy_2d_max_rate(legacy, variables, suction_pressure=suction_value),
            )


def test_3d_direct_matches_legacy():
    frame = pd.DataFrame(
        [
            [1000000, 50, 162, 52765],
            [1000000, 50, 258, 76928],
            [1000000, 50, 394, 118032],
            [1000000, 50, 471, 145965],
            [3000000, 50, 237, 71918],
            [3000000, 50, 258, 109823],
            [3000000, 50, 449, 137651],
            [7000000, 50, 322, 139839],
            [1000000, 51, 166, 53000],
            [1000000, 51, 480, 148000],
            [1000000, 52, 171, 54441],
            [1000000, 52, 215, 65205],
            [1000000, 52, 336, 98692],
            [1000000, 52, 487, 151316],
            [3000000, 52, 249, 74603],
            [3000000, 52, 384, 114277],
            [3000000, 52, 466, 143135],
            [7200000, 52, 362, 144574],
        ],
        columns=[RATE_NAME, PS_NAME, PD_NAME, "ENERGY"],
    )
    legacy = CompressorModelSampled3D(frame, "ENERGY")
    common = SampledCompressor3D(
        frame[[RATE_NAME, PS_NAME, PD_NAME]].to_numpy(dtype=np.float64), frame["ENERGY"].to_numpy(dtype=np.float64)
    )

    evaluations = {
        "rate": [1e6, 1e6, 1e6, 1e6, 1e6, 2e6],
        "suction_pressure": [50, 52, 53, 50, 50.5, 50],
        "discharge_pressure": [162, 150, 150, 432.5, 162, 162],
    }
    for query in _scalar_evaluation_cases(evaluations):
        _assert_allclose(common.evaluate(**query), _legacy_direct_evaluate(legacy, **query))
        common_projected = common.project_variables(
            rate=query["rate"] / common._scale_factor_rate,
            suction_pressure=query["suction_pressure"],
            discharge_pressure=query["discharge_pressure"],
        )
        legacy_projected = _legacy_3d_project(
            legacy,
            rate=query["rate"] / legacy._scale_factor_rate,
            suction_pressure=query["suction_pressure"],
            discharge_pressure=query["discharge_pressure"],
        )
        _assert_allclose(common_projected[0], legacy_projected[0])
        _assert_allclose(common_projected[1], legacy_projected[1])
        _assert_allclose(common_projected[2], legacy_projected[2])

    for suction_value, discharge_value in zip(
        [50, 50, 50, 51, 52, 52, 52],
        [471, 449, 322, 480, 487, 466, 362],
        strict=True,
    ):
        _assert_allclose(
            common.get_max_rate(
                suction_pressure=suction_value,
                discharge_pressure=discharge_value,
            ),
            _legacy_3d_max_rate(
                legacy,
                suction_pressure=suction_value,
                discharge_pressure=discharge_value,
            ),
        )
    out_of_range_ps, out_of_range_pd = np.meshgrid(
        np.asarray([45.0, 48.0, 50.0, 52.0, 55.0, 58.0], dtype=np.float64),
        np.asarray([100.0, 200.0, 300.0, 400.0, 500.0, 600.0], dtype=np.float64),
    )
    for suction_value, discharge_value in zip(out_of_range_ps.ravel(), out_of_range_pd.ravel(), strict=True):
        _assert_allclose(
            common.get_max_rate(
                suction_pressure=float(suction_value),
                discharge_pressure=float(discharge_value),
            ),
            _legacy_3d_max_rate(
                legacy,
                suction_pressure=float(suction_value),
                discharge_pressure=float(discharge_value),
            ),
        )


def test_power_interpolation():
    # power_interpolation_values map energy_usage (not rate) to power - using distinct
    # rate/energy_usage values here (rather than numerically identical ones) makes that
    # unambiguous.
    model = SampledCompressor(
        energy_usage_values=[20.0, 30.0, 40.0],
        rate_values=[2.0, 3.0, 4.0],
        power_interpolation_values=[200.0, 300.0, 400.0],
    )
    # Inside the sampled range: power = 10x the interpolated energy usage.
    for rate, expected_energy_usage, expected_power in [(2.0, 20.0, 200.0), (3.0, 30.0, 300.0), (4.0, 40.0, 400.0)]:
        result = model.evaluate(rate=rate, suction_pressure=1.0, discharge_pressure=1.0)
        assert result.power is not None
        _assert_allclose(result.energy_usage, expected_energy_usage)
        _assert_allclose(result.power, expected_power)

    # Below the lowest sampled rate: both energy usage and power extrapolate to 0.
    below_range = model.evaluate(rate=0.0, suction_pressure=1.0, discharge_pressure=1.0)
    assert below_range.power is not None
    _assert_allclose(below_range.energy_usage, 0.0)
    _assert_allclose(below_range.power, 0.0)

    # Above the highest sampled rate: both are NaN (no extrapolation for power).
    above_range = model.evaluate(rate=5.0, suction_pressure=1.0, discharge_pressure=1.0)
    assert above_range.power is not None
    assert np.isnan(above_range.energy_usage)
    assert np.isnan(above_range.power)


def test_get_max_standard_rate_matches_legacy():
    data = {
        "energy_usage_values": [52765, 71918, 139839, 144574],
        "rate_values": [1e6, 3e6, 7e6, 7.2e6],
    }
    common = SampledCompressor(**data)
    for suction_pressure, discharge_pressure in [(1.0, 1.0), (2.0, 2.0)]:
        _assert_allclose(
            common.get_max_standard_rate(
                suction_pressure=suction_pressure,
                discharge_pressure=discharge_pressure,
            ),
            _legacy_max_rate(
                data,
                suction_pressure=suction_pressure,
                discharge_pressure=discharge_pressure,
            ),
        )


def test_get_max_standard_rate_returns_nan_when_rate_not_provided():
    # With no RATE column at all, "maximum rate" is meaningless - get_max_standard_rate
    # must report that (NaN), not raise or silently return something else.
    model = SampledCompressor(
        energy_usage_values=[100.0, 150.0, 200.0],
        suction_pressure_values=[10.0, 20.0, 30.0],
        discharge_pressure_values=[60.0, 60.0, 60.0],
    )
    assert math.isnan(model.get_max_standard_rate(suction_pressure=20.0, discharge_pressure=60.0))


def test_get_max_standard_rate_returns_constant_when_rate_is_degenerate():
    # RATE is provided but identical across every sample (degenerate, not a real active
    # variable) - get_max_standard_rate must return that constant value, not NaN or an
    # error, since RATE still meaningfully bounds every operating point.
    model = SampledCompressor(
        energy_usage_values=[100.0, 150.0, 200.0],
        rate_values=[5000.0, 5000.0, 5000.0],
        suction_pressure_values=[10.0, 20.0, 30.0],
        discharge_pressure_values=[60.0, 60.0, 60.0],
    )
    _assert_allclose(model.get_max_standard_rate(suction_pressure=20.0, discharge_pressure=60.0), 5000.0)


def test_get_max_standard_rate_2d_matches_get_max_rate():
    # Unlike the 1D case above, legacy's CompressorModelSampled.get_max_standard_rate calls
    # get_max_rate() with no arguments, which only CompressorModelSampled1D supports -
    # CompressorModelSampled2D/3D.get_max_rate() require ps/pd and legacy raises TypeError,
    # so there is no legacy oracle for this dispatcher path. This is an intentional behaviour
    # change (SampledCompressor now forwards ps/pd instead of crashing); check it against the
    # underlying SampledCompressor2D.get_max_rate directly instead.
    data = {
        "energy_usage_values": [52765, 76928, 118032, 145965, 71918, 109823, 137651, 139839],
        "rate_values": [1e6, 1e6, 1e6, 1e6, 3e6, 3e6, 3e6, 7e6],
        "suction_pressure_values": [50] * 8,
        "discharge_pressure_values": [162, 258, 394, 471, 237, 258, 449, 322],
    }
    common = SampledCompressor(**data)
    assert isinstance(common._model, SampledCompressor2D)
    for suction_pressure, discharge_pressure in [(50.0, 162.0), (50.0, 300.0), (50.0, 471.0)]:
        _assert_allclose(
            common.get_max_standard_rate(
                suction_pressure=suction_pressure,
                discharge_pressure=discharge_pressure,
            ),
            common._model.get_max_rate(
                suction_pressure=suction_pressure,
                discharge_pressure=discharge_pressure,
            ),
        )


def test_get_max_standard_rate_3d_matches_get_max_rate():
    # Same rationale as test_get_max_standard_rate_2d_matches_get_max_rate above, but for the
    # 3D dispatch branch.
    frame = pd.DataFrame(
        [
            [1000000, 50, 162, 52765],
            [1000000, 50, 258, 76928],
            [1000000, 50, 394, 118032],
            [1000000, 50, 471, 145965],
            [3000000, 50, 237, 71918],
            [3000000, 50, 258, 109823],
            [3000000, 50, 449, 137651],
            [7000000, 50, 322, 139839],
            [1000000, 51, 166, 53000],
            [1000000, 51, 480, 148000],
            [1000000, 52, 171, 54441],
            [1000000, 52, 215, 65205],
            [1000000, 52, 336, 98692],
            [1000000, 52, 487, 151316],
            [3000000, 52, 249, 74603],
            [3000000, 52, 384, 114277],
            [3000000, 52, 466, 143135],
            [7200000, 52, 362, 144574],
        ],
        columns=[RATE_NAME, PS_NAME, PD_NAME, "ENERGY"],
    )
    common = SampledCompressor(
        energy_usage_values=frame["ENERGY"].tolist(),
        rate_values=frame[RATE_NAME].tolist(),
        suction_pressure_values=frame[PS_NAME].tolist(),
        discharge_pressure_values=frame[PD_NAME].tolist(),
    )
    assert isinstance(common._model, SampledCompressor3D)
    for suction_pressure, discharge_pressure in [(50.0, 471.0), (50.0, 322.0), (51.0, 480.0), (52.0, 362.0)]:
        _assert_allclose(
            common.get_max_standard_rate(
                suction_pressure=suction_pressure,
                discharge_pressure=discharge_pressure,
            ),
            common._model.get_max_rate(
                suction_pressure=suction_pressure,
                discharge_pressure=discharge_pressure,
            ),
        )


def test_evaluate_at_max_standard_rate_matches_legacy():
    # Regression test: evaluating exactly at get_max_standard_rate()'s own output lands on
    # a boundary where the minimum-rate and maximum-rate conditions can both hold (e.g. at
    # a hull corner, or wherever the two boundary surfaces cross). Legacy resolves this by
    # applying the minimum-rate branch first and letting the maximum-rate branch overwrite
    # it; an earlier scalar rewrite instead returned as soon as the minimum-rate branch
    # matched, silently picking the wrong surface. This is a normal, reachable query (e.g.
    # crossover/consumer-system logic evaluating at the reported maximum rate), not a
    # pathological edge case.
    data = {
        "energy_usage_values": [70000.0, 80000.0, 30000.0, 100000.0],
        "rate_values": [7000000.0, 5000000.0, 8000000.0, 6500000.0],
        "suction_pressure_values": [40.0, 55.0, 70.0, 50.0],
        "discharge_pressure_values": [250.0, 300.0, 230.0, 110.0],
    }
    common = SampledCompressor(
        energy_usage_values=data["energy_usage_values"],
        rate_values=data["rate_values"],
        suction_pressure_values=data["suction_pressure_values"],
        discharge_pressure_values=data["discharge_pressure_values"],
    )
    for suction_pressure, discharge_pressure in [(75.0, 100.0), (60.0, 150.0), (45.0, 280.0), (65.0, 200.0)]:
        max_rate = common.get_max_standard_rate(
            suction_pressure=suction_pressure, discharge_pressure=discharge_pressure
        )
        _assert_allclose(
            common.evaluate(
                rate=max_rate, suction_pressure=suction_pressure, discharge_pressure=discharge_pressure
            ).energy_usage,
            _legacy_evaluate(
                data, rate=max_rate, suction_pressure=suction_pressure, discharge_pressure=discharge_pressure
            ),
        )


def test_missing_variable_raises() -> None:
    with pytest.raises(ProcessMissingVariableValidationException):
        SampledCompressor(energy_usage_values=[1.0, 2.0, 3.0])


def test_mismatched_lengths_raises() -> None:
    with pytest.raises(ProcessEqualLengthValidationException):
        SampledCompressor(energy_usage_values=[1.0, 2.0, 3.0], rate_values=[1.0, 2.0])


def test_non_numeric_value_raises() -> None:
    with pytest.raises(InvalidColumnException):
        SampledCompressor(
            energy_usage_values=[1.0, 2.0, "not-a-number"],  # type: ignore[list-item]
            rate_values=[1.0, 2.0, 3.0],
        )


def test_negative_value_raises() -> None:
    with pytest.raises(ProcessNegativeValuesValidationException):
        SampledCompressor(energy_usage_values=[1.0, 2.0, -3.0], rate_values=[1.0, 2.0, 3.0])


def test_all_degenerate_variables_raises() -> None:
    with pytest.raises(IllegalStateException, match="non-degenerate"):
        SampledCompressor(energy_usage_values=[1.0, 2.0, 3.0], rate_values=[1.0, 1.0, 1.0])


def test_1d_duplicate_points_raises() -> None:
    with pytest.raises(IllegalStateException, match="non-unique"):
        SampledCompressor1D(RATE_NAME, np.asarray([1.0, 1.0, 2.0]), np.asarray([1.0, 2.0, 3.0]))
