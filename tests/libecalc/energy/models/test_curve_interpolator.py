import math

import pytest

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.energy.models.curve_interpolator import CurveInterpolator

VARIABLE = [0.0, 1000.0, 2000.0, 3000.0]
ENERGIES = [0.0, 10000.0, 18000.0, 25000.0]


def test_interpolates_linearly_between_points():
    model = CurveInterpolator(VARIABLE, ENERGIES)
    assert model.energy_for_variable(1500) == pytest.approx(14000)
    assert model.energy_for_variable(0) == 0.0
    assert model.energy_for_variable(1000) == pytest.approx(10000)


def test_above_range_is_nan():
    model = CurveInterpolator(VARIABLE, ENERGIES)
    assert math.isnan(model.energy_for_variable(3001))


def test_below_range_is_nan():
    model = CurveInterpolator([1000.0, 2000.0], [10000.0, 20000.0])
    assert math.isnan(model.energy_for_variable(0))


def test_negative_variable_below_range_is_nan():
    assert math.isnan(CurveInterpolator(VARIABLE, ENERGIES).energy_for_variable(-1))


def test_nan_variable_is_nan():
    assert math.isnan(CurveInterpolator(VARIABLE, ENERGIES).energy_for_variable(float("nan")))


@pytest.mark.parametrize(
    ("variable", "energies"),
    [
        ([0, 1], [0, 1, 2]),
        ([0], [0]),
        ([0, 2, 2], [0, 1, 2]),
        ([2, 1], [1, 2]),
        ([-1, 1], [0, 1]),
        ([0, 1], [0, -1]),
        ([0, float("nan")], [0, 1]),
        ([0, 1], [0, float("inf")]),
    ],
    ids=[
        "unequal_lengths",
        "single_point",
        "variable_not_increasing",
        "variable_descending",
        "negative_first_variable",
        "negative_energy",
        "non_finite_variable",
        "non_finite_energy",
    ],
)
def test_rejects_invalid_curve(variable, energies):
    with pytest.raises(EcalcValidationException):
        CurveInterpolator(variable, energies)
