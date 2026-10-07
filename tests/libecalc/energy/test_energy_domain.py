"""Tests energy domain contracts and energy type safety."""

from __future__ import annotations

import pytest

from libecalc.energy import (
    DieselRate,
    ElectricalPower,
    FuelGasRate,
    MechanicalPower,
)
from libecalc.energy.errors import NegativeEnergyError, NonFiniteEnergyError


class TestEnergyDomainContracts:
    """Tests that the ABCs enforce their contracts — the reason they exist."""

    def test_type_safety_prevents_mixing_energy_types(self):
        """Runtime guard on Energy.__add__ for dynamic contexts where the type checker can't help.

        ElectricalPower and MechanicalPower are both MW, but represent different
        energy forms — adding them is physically meaningless.
        """
        electrical = ElectricalPower(10.0)
        mechanical = MechanicalPower(5.0)

        with pytest.raises(TypeError):
            electrical + mechanical  # type: ignore[operator]

        # Same type works
        assert (electrical + ElectricalPower(5.0)).value == 15.0

    def test_type_safety_prevents_comparing_energy_types(self):
        """Runtime guard on Energy comparisons, mirroring the guard on addition.

        Ordering is restricted to one energy form so it stays total. Equality already
        requires the same type, so allowing cross-form ordering would leave a < b,
        a > b and a == b all false for two equal magnitudes.
        """
        electrical = ElectricalPower(10.0)
        mechanical = MechanicalPower(10.0)

        with pytest.raises(TypeError):
            _ = electrical < mechanical  # type: ignore[operator]

        assert electrical != mechanical

        # Same type orders on value
        assert ElectricalPower(5.0) < electrical
        assert electrical >= ElectricalPower(10.0)
        assert min(electrical, ElectricalPower(5.0)) == ElectricalPower(5.0)


class TestEnergyValueValidation:
    @pytest.mark.parametrize("energy_type", [ElectricalPower, MechanicalPower, FuelGasRate, DieselRate])
    @pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
    def test_rejects_non_finite_values(self, energy_type, value):
        with pytest.raises(NonFiniteEnergyError):
            energy_type(value)

    def test_rejects_negative_values(self):
        with pytest.raises(NegativeEnergyError):
            ElectricalPower(-1.0)

    def test_accepts_zero(self):
        assert ElectricalPower(0.0).value == 0.0
