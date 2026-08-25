"""Test energy domain ABCs using a simplified version of the ltp_export example.

INST_A topology (energy flow):

    fuel_gas_sac (Source[FuelGasRate]) — unlimited
        ├── genset (Converter[FuelGasRate, ElectricalPower]) — 17 MW capacity, 5000 Sm3/d per MW
        │       ├── base_load (Consumer[ElectricalPower])                    6 MW
        │       ├── steamgen (Consumer[ElectricalPower])                     5 MW
        │       ├── heating_sat_a (Consumer[ElectricalPower])                3 MW
        │       └── waterinj_motor (Converter[ElectricalPower, MechanicalPower]) — 5 MW, 95% eff
        │               └── waterinj (Consumer[MechanicalPower])             4 MW
        │
        ├── export_turbine (Converter[FuelGasRate, MechanicalPower]) — 30 MW, 6000 Sm3/d per MW
        │       └── export_compressor (Consumer[MechanicalPower])           20 MW
        │
        └── gascompression_compressor_sampled (Consumer[FuelGasRate]) — sampled, 50000 Sm3/d

    flare_gas (Source[FuelGasRate]) — unlimited
        └── flare (Consumer[FuelGasRate])                                 1200 Sm3/d

    diesel (Source[DieselRate]) — unlimited
        └── diesel_consumers (Consumer[DieselRate])                        500 l/d

    onshore_power (Source[ElectricalPower]) — 20 MW capacity ──┐
    wind_turbine (Source[ElectricalPower]) — 4.4 MW capacity ──┤ power_from_shore bus
                                                               └── heating (Consumer[ElectricalPower])  10 MW

    Cold venting, fugitives, loading, storage → emission domain (not energy).
"""

from __future__ import annotations

from typing import Final

import pytest

from libecalc.energy import (
    Consumer,
    Converter,
    ElectricalPower,
    FuelGasRate,
    MechanicalPower,
    Provider,
    Source,
)
from libecalc.energy.demand import Demand, DieselRate
from libecalc.energy.energy_unit import EnergyUnitId

# --- Test implementations (illustrative, not shipped as library code) ---


class FuelGasSource(Source[FuelGasRate]):
    def __init__(self, name: str, energy_unit_id: EnergyUnitId | None = None) -> None:
        self.name = name
        self._id: Final[EnergyUnitId] = energy_unit_id or FuelGasSource._create_id()

    def get_id(self) -> EnergyUnitId:
        return self._id

    def get_name(self) -> str:
        return self.name

    def capacity(self) -> FuelGasRate | None:
        return None


class PowerFromShore(Source[ElectricalPower]):
    def __init__(self, name: str, max_power_mw: float, energy_unit_id: EnergyUnitId | None = None) -> None:
        self.name = name
        self.max_power_mw = max_power_mw
        self._id: Final[EnergyUnitId] = energy_unit_id or PowerFromShore._create_id()

    def get_id(self) -> EnergyUnitId:
        return self._id

    def get_name(self) -> str:
        return self.name

    def capacity(self) -> ElectricalPower | None:
        return ElectricalPower(self.max_power_mw)


class WindTurbine(Source[ElectricalPower]):
    def __init__(self, name: str, power_mw: float, energy_unit_id: EnergyUnitId | None = None) -> None:
        self.name = name
        self.power_mw = power_mw
        self._id: Final[EnergyUnitId] = energy_unit_id or WindTurbine._create_id()

    def get_id(self) -> EnergyUnitId:
        return self._id

    def get_name(self) -> str:
        return self.name

    def capacity(self) -> ElectricalPower | None:
        return ElectricalPower(self.power_mw)


class GeneratorSet(Converter[FuelGasRate, ElectricalPower]):
    def __init__(
        self, name: str, max_power_mw: float, fuel_per_mw: float, energy_unit_id: EnergyUnitId | None = None
    ) -> None:
        self.name = name
        self.max_power_mw = max_power_mw
        self.fuel_per_mw = fuel_per_mw
        self._id: Final[EnergyUnitId] = energy_unit_id or GeneratorSet._create_id()

    def get_id(self) -> EnergyUnitId:
        return self._id

    def get_name(self) -> str:
        return self.name

    def capacity(self) -> ElectricalPower | None:
        return ElectricalPower(self.max_power_mw)

    def get_input_demand(self, output_demand: ElectricalPower) -> FuelGasRate:
        return FuelGasRate(output_demand.value * self.fuel_per_mw)


class GasTurbine(Converter[FuelGasRate, MechanicalPower]):
    def __init__(
        self, name: str, max_power_mw: float, fuel_per_mw: float, energy_unit_id: EnergyUnitId | None = None
    ) -> None:
        self.name = name
        self.max_power_mw = max_power_mw
        self.fuel_per_mw = fuel_per_mw
        self._id: Final[EnergyUnitId] = energy_unit_id or GasTurbine._create_id()

    def get_id(self) -> EnergyUnitId:
        return self._id

    def get_name(self) -> str:
        return self.name

    def capacity(self) -> MechanicalPower | None:
        return MechanicalPower(self.max_power_mw)

    def get_input_demand(self, output_demand: MechanicalPower) -> FuelGasRate:
        return FuelGasRate(output_demand.value * self.fuel_per_mw)


class ElectricalMotor(Converter[ElectricalPower, MechanicalPower]):
    def __init__(
        self, name: str, max_power_mw: float, efficiency: float = 0.95, energy_unit_id: EnergyUnitId | None = None
    ) -> None:
        self.name = name
        self.max_power_mw = max_power_mw
        self.efficiency = efficiency
        self._id: Final[EnergyUnitId] = energy_unit_id or ElectricalMotor._create_id()

    def get_id(self) -> EnergyUnitId:
        return self._id

    def get_name(self) -> str:
        return self.name

    def capacity(self) -> MechanicalPower | None:
        return MechanicalPower(self.max_power_mw * self.efficiency)

    def get_input_demand(self, output_demand: MechanicalPower) -> ElectricalPower:
        return ElectricalPower(output_demand.value / self.efficiency)


class BaseLoad(Consumer[ElectricalPower]):
    def __init__(self, name: str, load_mw: float, energy_unit_id: EnergyUnitId | None = None) -> None:
        self.name = name
        self.load_mw = load_mw
        self._id: Final[EnergyUnitId] = energy_unit_id or BaseLoad._create_id()

    def get_id(self) -> EnergyUnitId:
        return self._id

    def get_name(self) -> str:
        return self.name

    def get_demand(self) -> ElectricalPower:
        return ElectricalPower(self.load_mw)


class Compressor(Consumer[MechanicalPower]):
    def __init__(self, name: str, power_mw: float, energy_unit_id: EnergyUnitId | None = None) -> None:
        self.name = name
        self.power_mw = power_mw
        self._id: Final[EnergyUnitId] = energy_unit_id or Compressor._create_id()

    def get_id(self) -> EnergyUnitId:
        return self._id

    def get_name(self) -> str:
        return self.name

    def get_demand(self) -> MechanicalPower:
        return MechanicalPower(self.power_mw)


class Pump(Consumer[MechanicalPower]):
    def __init__(self, name: str, power_mw: float, energy_unit_id: EnergyUnitId | None = None) -> None:
        self.name = name
        self.power_mw = power_mw
        self._id: Final[EnergyUnitId] = energy_unit_id or Pump._create_id()

    def get_id(self) -> EnergyUnitId:
        return self._id

    def get_name(self) -> str:
        return self.name

    def get_demand(self) -> MechanicalPower:
        return MechanicalPower(self.power_mw)


class SampledCompressor(Consumer[FuelGasRate]):
    def __init__(self, name: str, fuel_rate: float, energy_unit_id: EnergyUnitId | None = None) -> None:
        self.name = name
        self.fuel_rate = fuel_rate
        self._id: Final[EnergyUnitId] = energy_unit_id or SampledCompressor._create_id()

    def get_id(self) -> EnergyUnitId:
        return self._id

    def get_name(self) -> str:
        return self.name

    def get_demand(self) -> FuelGasRate:
        return FuelGasRate(self.fuel_rate)


class Flare(Consumer[FuelGasRate]):
    def __init__(self, name: str, fuel_rate: float, energy_unit_id: EnergyUnitId | None = None) -> None:
        self.name = name
        self.fuel_rate = fuel_rate
        self._id: Final[EnergyUnitId] = energy_unit_id or Flare._create_id()

    def get_id(self) -> EnergyUnitId:
        return self._id

    def get_name(self) -> str:
        return self.name

    def get_demand(self) -> FuelGasRate:
        return FuelGasRate(self.fuel_rate)


class DieselConsumer(Consumer[DieselRate]):
    def __init__(self, name: str, fuel_rate: float, energy_unit_id: EnergyUnitId | None = None) -> None:
        self.name = name
        self.fuel_rate = fuel_rate
        self._id: Final[EnergyUnitId] = energy_unit_id or DieselConsumer._create_id()

    def get_id(self) -> EnergyUnitId:
        return self._id

    def get_name(self) -> str:
        return self.name

    def get_demand(self) -> DieselRate:
        return DieselRate(self.fuel_rate)


class ElectricalBus(Provider[ElectricalPower]):
    def __init__(
        self,
        name: str,
        sources: list[Source[ElectricalPower]] | None = None,
        consumers: list[Consumer[ElectricalPower]] | None = None,
        *,
        energy_unit_id: EnergyUnitId | None = None,
    ) -> None:
        self.name = name
        self.sources = sources or []
        self.consumers = consumers or []
        self._id: Final[EnergyUnitId] = energy_unit_id or ElectricalBus._create_id()

    def get_id(self) -> EnergyUnitId:
        return self._id

    def get_name(self) -> str:
        return self.name

    def capacity(self) -> ElectricalPower | None:
        result = ElectricalPower(0)
        for source in self.sources:
            c = source.capacity()
            if c is None:
                return None
            result = result + c
        return result

    def total_demand(self) -> ElectricalPower:
        result = ElectricalPower(0)
        for consumer in self.consumers:
            result = result + consumer.get_demand()
        return result


# --- Tests ---


class TestABCContracts:
    """Tests that the ABCs enforce their contracts — the reason they exist."""

    def test_converters_are_substitutable(self):
        """Any Converter[FuelGasRate, T] can be used polymorphically.

        This is the value proposition: code operating on the abstract interface
        works across all concrete implementations without knowing the type.
        """

        def fuel_required[TProvides: Demand](
            converter: Converter[FuelGasRate, TProvides], demand: TProvides
        ) -> FuelGasRate:
            return converter.get_input_demand(demand)

        genset = GeneratorSet("genset", max_power_mw=17.0, fuel_per_mw=5000.0)
        turbine = GasTurbine("turbine", max_power_mw=30.0, fuel_per_mw=6000.0)

        assert fuel_required(genset, ElectricalPower(10.0)).value == 50_000.0
        assert fuel_required(turbine, MechanicalPower(10.0)).value == 60_000.0

    def test_type_safety_prevents_mixing_energy_types(self):
        """Runtime guard on Demand.__add__ for dynamic contexts where the type checker can't help.

        ElectricalPower and MechanicalPower are both MW, but represent different
        energy forms — adding them is physically meaningless.
        """
        electrical = ElectricalPower(10.0)
        mechanical = MechanicalPower(5.0)

        with pytest.raises(TypeError):
            electrical + mechanical  # type: ignore[operator]

        # Same type works
        assert (electrical + ElectricalPower(5.0)).value == 15.0


class TestEnergyTopology:
    """Tests that the ABCs compose into a real energy topology."""

    def test_demand_propagates_through_full_installation(self):
        """Wire INST_A and verify demand traces back to fuel sources.

        The invariant: every consumer's demand propagates through converters
        to a source, accumulating conversion losses along the way.
        """
        genset = GeneratorSet("genset", max_power_mw=17.0, fuel_per_mw=5000.0)
        motor = ElectricalMotor("waterinj_motor", max_power_mw=5.0, efficiency=0.95)
        turbine = GasTurbine("export_turbine", max_power_mw=30.0, fuel_per_mw=6000.0)

        # Electrical consumers on genset (including pump through motor)
        electrical_demand = (
            BaseLoad("base_load", load_mw=6.0).get_demand()
            + BaseLoad("steamgen", load_mw=5.0).get_demand()
            + BaseLoad("heating_sat_a", load_mw=3.0).get_demand()
            + motor.get_input_demand(Pump("waterinj", power_mw=4.0).get_demand())
        )

        # All chains resolve to FuelGasRate
        genset_fuel = genset.get_input_demand(electrical_demand)
        export_fuel = turbine.get_input_demand(Compressor("export", power_mw=20.0).get_demand())
        sampled_fuel = SampledCompressor("gascompression", fuel_rate=50_000.0).get_demand()

        # Motor overhead propagates: 4 MW pump → 4/0.95 MW electrical → fuel
        total_fuel = genset_fuel + export_fuel + sampled_fuel
        assert isinstance(total_fuel, FuelGasRate)
        assert total_fuel.value > 50_000.0 + 120_000.0  # more than direct sum due to motor loss

    def test_infeasibility_is_detectable_but_not_enforced(self):
        """Capacity enables feasibility checking, but converters don't cap.

        Design decision: compute full demand regardless of capacity so emissions
        reporting reflects the intended operational point. The solver flags infeasibility.
        """
        genset = GeneratorSet("genset", max_power_mw=17.0, fuel_per_mw=5000.0)
        demand = ElectricalPower(18.0)  # exceeds 17 MW capacity

        # Infeasibility is detectable
        assert genset.capacity() is not None
        assert demand.value > genset.capacity().value

        # But get_input_demand still computes — no capping
        fuel = genset.get_input_demand(demand)
        assert fuel.value == 18.0 * 5000.0

    def test_bus_aggregates_finite_source_capacities(self):
        """Bus capacity is the sum of its sources' capacities."""
        bus = ElectricalBus(
            name="power_from_shore",
            sources=[
                PowerFromShore("onshore_power", max_power_mw=20.0),
                WindTurbine("wind_turbine", power_mw=4.4),
            ],
            consumers=[BaseLoad("heating", load_mw=10.0)],
        )

        capacity = bus.capacity()
        demand = bus.total_demand()

        assert capacity is not None
        assert capacity.value == 24.4
        assert demand.value <= capacity.value
