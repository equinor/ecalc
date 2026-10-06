import numpy as np
import pytest

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.domain.infrastructure.energy_components.generator_set.generator_set_model import GeneratorSetModel
from libecalc.energy.models.generator_set_fuel_model import GeneratorSetFuelModel
from libecalc.presentation.yaml.yaml_entities import MemoryResource

POWERS = [0.0, 4.0, 8.0, 12.0]
FUELS = [0.0, 20000.0, 38000.0, 55000.0]


@pytest.mark.parametrize(
    ("powers", "fuels"),
    [(POWERS, FUELS), ([2.0, 4.0, 8.0], [10000.0, 20000.0, 38000.0])],
    ids=["from_zero", "below_first_power"],
)
def test_fuel_matches_legacy_generator_set(powers, fuels):
    fuel_model = GeneratorSetFuelModel(powers, fuels)
    legacy = GeneratorSetModel(name="legacy", resource=MemoryResource(data=[fuels, powers], headers=["FUEL", "POWER"]))
    evaluated_powers = np.array([0.0, 0.5, 2.0, 3.0, 5.0, 8.0, 11.0, 12.0, 20.0])

    assert [fuel_model.fuel_for_power(power) for power in evaluated_powers] == pytest.approx(
        [legacy.evaluate_fuel_usage(power) for power in evaluated_powers]
    )
    assert fuel_model.max_power == pytest.approx(legacy.max_capacity)


def test_negative_power_is_rejected():
    with pytest.raises(AssertionError, match="negative"):
        GeneratorSetFuelModel(POWERS, FUELS).fuel_for_power(-1)


@pytest.mark.parametrize(
    ("powers", "fuels"),
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
        "powers_not_increasing",
        "powers_descending",
        "negative_first_power",
        "negative_fuel",
        "non_finite_power",
        "non_finite_fuel",
    ],
)
def test_rejects_invalid_generator_set(powers, fuels):
    with pytest.raises(EcalcValidationException):
        GeneratorSetFuelModel(powers, fuels)
