import numpy as np
import pytest

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.domain.infrastructure.energy_components.turbine.turbine import Turbine
from libecalc.energy.models.turbine_fuel_model import TurbineFuelModel

LOADS = [2.352, 4.589, 6.853]
EFFICIENCIES = [0.138, 0.210, 0.255]


@pytest.mark.parametrize(
    ("loads", "efficiencies"),
    [(LOADS, EFFICIENCIES), ([2, 10], [0.2, 0.3])],
    ids=["datasheet_curve", "below_first_load"],
)
def test_fuel_matches_legacy_turbine_from_first_load(loads, efficiencies):
    fuel_model = TurbineFuelModel(loads, efficiencies, 38)
    legacy = Turbine(
        loads=loads,
        lower_heating_value=38,
        efficiency_fractions=efficiencies,
        energy_usage_adjustment_factor=1,
        energy_usage_adjustment_constant=0,
    )
    powers = np.array([power for power in [0.0, 2.0, 3.0, 5.0, 7.0, 12.0] if power == 0 or power >= loads[0]])

    expected = legacy.evaluate(powers).get_energy_result().energy_usage.values

    assert [fuel_model.fuel_for_power(power) for power in powers] == pytest.approx(list(expected))
    assert fuel_model.max_power == pytest.approx(legacy.max_power)


def test_below_first_load_burns_the_fuel_of_the_first_load():
    fuel_model = TurbineFuelModel([2, 10], [0.2, 0.3], 38)

    assert fuel_model.fuel_for_power(0.5) == pytest.approx(fuel_model.fuel_for_power(2))
    assert fuel_model.fuel_for_power(0.5) > 0


def test_zero_power_burns_no_fuel():
    assert TurbineFuelModel([2, 10], [0.2, 0.3], 38).fuel_for_power(0) == 0.0


def test_negative_power_is_rejected():
    with pytest.raises(AssertionError, match="negative"):
        TurbineFuelModel([2, 10], [0.2, 0.3], 38).fuel_for_power(-1)


@pytest.mark.parametrize(
    ("loads", "efficiencies", "lhv"),
    [
        ([0, 1], [0.1, 0.2, 0.3], 38),
        ([1], [0.1], 38),
        ([0, 2, 2], [0.1, 0.2, 0.3], 38),
        ([0, 1, 2], [0.1, 0.2, 1.2], 38),
        ([1, 2, 3], [0.1, 0, 0.3], 38),
        ([0, 1, float("nan")], [0.1, 0.2, 0.3], 38),
        ([0, 1, 2], [0.1, 0.2, 0.3], 0),
        ([0, 1, 2], [0.1, 0.2, 0.3], float("inf")),
        ([-1, 1, 2], [0.1, 0.2, 0.3], 38),
    ],
    ids=[
        "unequal_lengths",
        "single_point",
        "loads_not_increasing",
        "efficiency_above_one",
        "zero_efficiency",
        "non_finite_load",
        "zero_heating_value",
        "infinite_heating_value",
        "negative_first_load",
    ],
)
def test_rejects_invalid_turbine(loads, efficiencies, lhv):
    with pytest.raises(EcalcValidationException):
        TurbineFuelModel(loads, efficiencies, lhv)
