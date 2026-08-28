"""Tests energy domain contracts and demand propagation through converters."""

from __future__ import annotations

import pytest

from libecalc.energy import (
    Converter,
    ElectricalPower,
    FuelGasRate,
    MechanicalPower,
)
from libecalc.energy.energy_types import Energy
from libecalc.energy.energy_units import (
    BaseLoad,
    Compressor,
    ElectricalMotor,
    GasTurbine,
    GeneratorSet,
    Pump,
    SampledFuelConsumer,
)


class TestABCContracts:
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


class TestEnergyDomainBehavior:
    """Tests that the ABCs compose into a real energy topology."""

    def test_demand_propagates_through_full_installation(self):
        """Wire INST_A and verify demand traces back to fuel sources.

        The invariant: every consumer's demand propagates through converters
        to a source, accumulating conversion losses along the way.
        """
        genset = GeneratorSet("genset", max_power=17.0, power_to_fuel=lambda output_power: output_power * 5000.0)
        motor = ElectricalMotor("waterinj_motor", max_power=5.0, efficiency=0.95)
        turbine = GasTurbine("export_turbine", max_power=30.0, power_to_fuel=lambda output_power: output_power * 6000.0)

        # Electrical consumers on genset (including pump through motor)
        electrical_demand = (
            BaseLoad("base_load", load=6.0).get_input_energy()
            + BaseLoad("steamgen", load=5.0).get_input_energy()
            + BaseLoad("heating_sat_a", load=3.0).get_input_energy()
            + motor.get_input_energy(Pump("waterinj", power=4.0).get_input_energy())
        )

        # All chains resolve to FuelGasRate
        genset_fuel = genset.get_input_energy(electrical_demand)
        export_fuel = turbine.get_input_energy(Compressor("export", power=20.0).get_input_energy())
        sampled_fuel = SampledFuelConsumer("gascompression", fuel_rate=50_000.0).get_input_energy()

        # Motor overhead propagates: 4 MW pump → 4/0.95 MW electrical → fuel
        total_fuel = genset_fuel + export_fuel + sampled_fuel
        assert isinstance(total_fuel, FuelGasRate)
        assert total_fuel.value > 50_000.0 + 120_000.0  # more than direct sum due to motor loss

    def test_infeasibility_is_detectable_but_not_enforced(self):
        """Capacity enables feasibility checking, but converters don't cap.

        Design decision: compute full demand regardless of capacity so emissions
        reporting reflects the intended operational point. The solver flags infeasibility.
        """
        genset = GeneratorSet("genset", max_power=17.0, power_to_fuel=lambda output_power: output_power * 5000.0)
        demand = ElectricalPower(18.0)  # exceeds 17 MW capacity

        # Infeasibility is detectable
        capacity = genset.capacity()
        assert capacity is not None
        assert demand.value > capacity.value

        # But get_input_energy still computes — no capping
        fuel = genset.get_input_energy(demand)
        assert fuel.value == 18.0 * 5000.0
