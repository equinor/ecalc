import numpy as np
import pytest

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.domain.infrastructure.energy_components.generator_set.generator_set_model import GeneratorSetModel
from libecalc.energy.models.combustion_engine_fuel_model import TurbineFuelModel
from libecalc.energy.models.generator_set_fuel_model import (
    EngineDrivenGeneratorSetFuelModel,
    SampledGeneratorSetFuelModel,
)
from libecalc.presentation.yaml.yaml_entities import MemoryResource

POWERS = [0.0, 4.0, 8.0, 12.0]
FUELS = [0.0, 20000.0, 38000.0, 55000.0]


@pytest.mark.parametrize(
    ("powers", "fuels"),
    [(POWERS, FUELS), ([2.0, 4.0, 8.0], [10000.0, 20000.0, 38000.0])],
    ids=["from_zero", "below_first_power"],
)
def test_fuel_matches_legacy_generator(powers, fuels):
    fuel_model = SampledGeneratorSetFuelModel(powers, fuels)
    legacy = GeneratorSetModel(name="legacy", resource=MemoryResource(data=[fuels, powers], headers=["FUEL", "POWER"]))
    evaluated_powers = np.array([0.0, 0.5, 2.0, 3.0, 5.0, 8.0, 11.0, 12.0, 20.0])

    assert [fuel_model.fuel_for_power(power) for power in evaluated_powers] == pytest.approx(
        [legacy.evaluate_fuel_usage(power) for power in evaluated_powers]
    )
    assert fuel_model.max_power == pytest.approx(legacy.max_capacity)


def test_negative_power_is_rejected():
    with pytest.raises(AssertionError, match="negative"):
        SampledGeneratorSetFuelModel(POWERS, FUELS).fuel_for_power(-1)


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
def test_rejects_invalid_generator(powers, fuels):
    with pytest.raises(EcalcValidationException):
        SampledGeneratorSetFuelModel(powers, fuels)


ENGINE_LOADS = [2.0, 4.0, 8.0, 12.0]
ENGINE_EFFICIENCIES = [0.3, 0.35, 0.4, 0.4]
LOWER_HEATING_VALUE = 38.0


def _engine_driven_model(generator_efficiency: float = 0.95) -> EngineDrivenGeneratorSetFuelModel:
    engine_fuel_model = TurbineFuelModel(ENGINE_LOADS, ENGINE_EFFICIENCIES, LOWER_HEATING_VALUE)
    return EngineDrivenGeneratorSetFuelModel(engine_fuel_model, generator_efficiency)


def test_engine_driven_max_power_is_scaled_by_generator_efficiency():
    engine_fuel_model = TurbineFuelModel(ENGINE_LOADS, ENGINE_EFFICIENCIES, LOWER_HEATING_VALUE)
    generator_efficiency = 0.95
    model = EngineDrivenGeneratorSetFuelModel(engine_fuel_model, generator_efficiency)

    assert model.max_power == pytest.approx(engine_fuel_model.max_power * generator_efficiency)


@pytest.mark.parametrize("generator_efficiency", [0.95, 0.5, 1.0])
def test_engine_driven_fuel_matches_engine_at_converted_load(generator_efficiency):
    engine_fuel_model = TurbineFuelModel(ENGINE_LOADS, ENGINE_EFFICIENCIES, LOWER_HEATING_VALUE)
    model = EngineDrivenGeneratorSetFuelModel(engine_fuel_model, generator_efficiency)

    electrical_power = 6.0
    expected_load = electrical_power / generator_efficiency

    assert model.fuel_for_power(electrical_power) == pytest.approx(engine_fuel_model.fuel_for_power(expected_load))


def test_engine_driven_clamps_to_first_load_below_curve():
    # Electrical power below efficiency * first load converts to a load below the curve's first point;
    # the underlying engine model clamps to the first load/efficiency instead of extrapolating.
    generator_efficiency = 0.95
    model = _engine_driven_model(generator_efficiency)
    below_curve_power = 0.5 * generator_efficiency

    at_first_point = model.fuel_for_power(ENGINE_LOADS[0] * generator_efficiency)
    below_curve = model.fuel_for_power(below_curve_power)

    assert below_curve == pytest.approx(at_first_point)


def test_engine_driven_zero_power_gives_zero_fuel():
    assert _engine_driven_model().fuel_for_power(0) == 0.0


def test_engine_driven_negative_power_is_rejected():
    with pytest.raises(AssertionError, match="negative"):
        _engine_driven_model().fuel_for_power(-1)


@pytest.mark.parametrize("generator_efficiency", [0, -0.1, 1.1, float("nan")])
def test_engine_driven_rejects_invalid_generator_efficiency(generator_efficiency):
    engine_fuel_model = TurbineFuelModel(ENGINE_LOADS, ENGINE_EFFICIENCIES, LOWER_HEATING_VALUE)
    with pytest.raises(EcalcValidationException, match="Generator efficiency"):
        EngineDrivenGeneratorSetFuelModel(engine_fuel_model, generator_efficiency)
