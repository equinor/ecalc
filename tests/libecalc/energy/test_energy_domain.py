"""Tests energy domain contracts and energy type safety."""

from __future__ import annotations

import pytest

from libecalc.energy import (
    Converter,
    ElectricalPower,
    MechanicalPower,
)
from libecalc.energy.energy_types import Energy
from libecalc.energy.energy_units import (
    GasTurbine,
    GeneratorSet,
)


class TestEnergyDomainContracts:
    """Tests that the ABCs enforce their contracts — the reason they exist."""

    def test_converters_are_substitutable(self):
        """Converters can be used polymorphically through the common Energy interface.

        This is the value proposition: code operating on the abstract interface
        works across all concrete implementations without knowing the type.
        """

        def required_input_energy(converter: Converter, output_energy: Energy) -> Energy:
            return converter.get_input_energy(output_energy)

        genset = GeneratorSet("genset", max_power=17.0, power_to_fuel=lambda output_power: output_power * 5000.0)
        turbine = GasTurbine("turbine", max_power=30.0, power_to_fuel=lambda output_power: output_power * 6000.0)

        assert required_input_energy(genset, ElectricalPower(10.0)).value == 50_000.0
        assert required_input_energy(turbine, MechanicalPower(10.0)).value == 60_000.0

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
