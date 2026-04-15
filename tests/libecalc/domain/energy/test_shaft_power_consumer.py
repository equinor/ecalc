"""Pure physics: enthalpy rise × mass rate → shaft power."""

from libecalc.domain.energy.rotating_equipment.shaft_power_consumer import ShaftPowerConsumer


def _make_consumer(
    inlet_enthalpy=200_000.0,
    outlet_enthalpy=250_000.0,
    mass_rate=36_000.0,
):
    """Default: Δh = 50 kJ/kg, ṁ = 36 000 kg/h (10 kg/s) → P = 0.5 MW."""
    return ShaftPowerConsumer(
        inlet_enthalpy_joule_per_kg=inlet_enthalpy,
        outlet_enthalpy_joule_per_kg=outlet_enthalpy,
        mass_rate_kg_per_h=mass_rate,
    )


class TestShaftPowerConsumer:
    def test_power_from_enthalpy_rise(self):
        """P = delta_h × mass_rate = 50kJ/kg × 10 kg/s = 0.5 MW."""
        assert _make_consumer().get_shaft_power_demand_mw() == 0.5

    def test_zero_rate(self):
        assert _make_consumer(mass_rate=0.0).get_shaft_power_demand_mw() == 0.0
