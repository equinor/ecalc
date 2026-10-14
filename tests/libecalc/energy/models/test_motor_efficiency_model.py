import pytest

from libecalc.common.errors.ecalc_validation_error import EcalcValidationException
from libecalc.energy.models.motor_efficiency_model import MotorEfficiencyModel


def test_electrical_power_uses_efficiency_interpolated_between_loads():
    model = MotorEfficiencyModel(loads=[1, 3, 5], efficiencies=[0.90, 0.95, 0.96])

    assert model.electrical_for_mechanical(2) == pytest.approx(2 / 0.925)


def test_electrical_power_uses_first_and_last_efficiency_outside_the_curve():
    model = MotorEfficiencyModel(loads=[1, 3, 5], efficiencies=[0.90, 0.95, 0.96])

    assert model.electrical_for_mechanical(0.5) == pytest.approx(0.5 / 0.90)
    assert model.electrical_for_mechanical(8) == pytest.approx(8 / 0.96)


def test_rejects_efficiency_above_one():
    with pytest.raises(EcalcValidationException, match="above 0 and up to 1"):
        MotorEfficiencyModel(loads=[1, 3], efficiencies=[0.90, 1.2])


def test_rejects_zero_efficiency():
    with pytest.raises(EcalcValidationException, match="above 0 and up to 1"):
        MotorEfficiencyModel(loads=[0, 3], efficiencies=[0, 0.95])
