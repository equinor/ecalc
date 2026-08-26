from typing import Final

import pytest

from libecalc.energy import Consumer, Converter, ElectricalPower, EnergyUnitId, FuelGasRate, Source
from libecalc.energy.network import EnergyConnection, EnergyNetwork


class FuelSource(Source[FuelGasRate]):
    def __init__(self, energy_unit_id: EnergyUnitId | None = None):
        self._id: Final[EnergyUnitId] = energy_unit_id or self._create_id()

    def get_id(self) -> EnergyUnitId:
        return self._id

    @property
    def provided_type(self) -> type[FuelGasRate]:
        return FuelGasRate

    def capacity(self) -> FuelGasRate | None:
        return None


class GeneratorSet(Converter[FuelGasRate, ElectricalPower]):
    def __init__(self, max_power_mw: float, fuel_per_mw: float, energy_unit_id: EnergyUnitId | None = None) -> None:
        self.max_power_mw = max_power_mw
        self.fuel_per_mw = fuel_per_mw
        self._id: Final[EnergyUnitId] = energy_unit_id or self._create_id()

    def get_id(self) -> EnergyUnitId:
        return self._id

    @property
    def required_type(self) -> type[FuelGasRate]:
        return FuelGasRate

    @property
    def provided_type(self) -> type[ElectricalPower]:
        return ElectricalPower

    def capacity(self) -> ElectricalPower | None:
        return ElectricalPower(self.max_power_mw)

    def get_input_demand(self, output_demand: ElectricalPower) -> FuelGasRate:
        return FuelGasRate(output_demand.value * self.fuel_per_mw)


class ElectricalLoad(Consumer[ElectricalPower]):
    def __init__(self, load_mw: float, energy_unit_id: EnergyUnitId | None = None) -> None:
        self.load_mw = load_mw
        self._id: Final[EnergyUnitId] = energy_unit_id or self._create_id()

    def get_id(self) -> EnergyUnitId:
        return self._id

    @property
    def required_type(self) -> type[ElectricalPower]:
        return ElectricalPower

    def get_demand(self) -> ElectricalPower:
        return ElectricalPower(self.load_mw)


class ElectricalPowerLoss(Converter[ElectricalPower, ElectricalPower]):
    def __init__(self, loss_factor: float, energy_unit_id: EnergyUnitId | None = None) -> None:
        self._id: Final[EnergyUnitId] = energy_unit_id or self._create_id()
        self.loss_factor = loss_factor

    def get_id(self) -> EnergyUnitId:
        return self._id

    @property
    def required_type(self) -> type[ElectricalPower]:
        return ElectricalPower

    @property
    def provided_type(self) -> type[ElectricalPower]:
        return ElectricalPower

    def capacity(self) -> ElectricalPower | None:
        return None

    def get_input_demand(
        self,
        output_demand: ElectricalPower,
    ) -> ElectricalPower:
        return ElectricalPower(output_demand.value / (1 - self.loss_factor))


def test_accepts_valid_typed_network():
    source = FuelSource()
    generator = GeneratorSet(max_power_mw=10, fuel_per_mw=5000)
    load = ElectricalLoad(load_mw=5)

    network = EnergyNetwork(
        nodes=[source, generator, load],
        connections=[
            EnergyConnection(
                source_id=source.get_id(),
                target_id=generator.get_id(),
            ),
            EnergyConnection(
                source_id=generator.get_id(),
                target_id=load.get_id(),
            ),
        ],
    )
    assert network.topological_order() == (
        source.get_id(),
        generator.get_id(),
        load.get_id(),
    )
    assert network.predecessors(load.get_id()) == frozenset({generator.get_id()})
    assert network.get_node(generator.get_id()) is generator


def test_rejects_incompatible_energy_types():
    source = FuelSource()
    load = ElectricalLoad(load_mw=5)

    with pytest.raises(
        ValueError,
        match="Incompatible energy types",
    ):
        EnergyNetwork(
            nodes=[source, load],
            connections=[
                EnergyConnection(
                    source_id=source.get_id(),
                    target_id=load.get_id(),
                )
            ],
        )


def test_rejects_unknown_source():
    load = ElectricalLoad(load_mw=5)
    missing_id = FuelSource._create_id()

    with pytest.raises(ValueError, match="Unknown source"):
        EnergyNetwork(
            nodes=[load],
            connections=[
                EnergyConnection(
                    source_id=missing_id,
                    target_id=load.get_id(),
                )
            ],
        )


def test_rejects_unknown_target():
    source = FuelSource()
    missing_id = ElectricalLoad._create_id()

    with pytest.raises(ValueError, match="Unknown target"):
        EnergyNetwork(
            nodes=[source],
            connections=[
                EnergyConnection(
                    source_id=source.get_id(),
                    target_id=missing_id,
                )
            ],
        )


def test_rejects_consumer_as_source():
    source = ElectricalLoad(load_mw=5)
    target = ElectricalLoad(load_mw=5)

    with pytest.raises(
        ValueError,
        match="Source node provides no energy",
    ):
        EnergyNetwork(
            nodes=[source, target],
            connections=[
                EnergyConnection(
                    source_id=source.get_id(),
                    target_id=target.get_id(),
                )
            ],
        )


def test_rejects_provider_as_target():
    source = FuelSource()
    target = FuelSource()

    with pytest.raises(
        ValueError,
        match="Target node requires no energy",
    ):
        EnergyNetwork(
            nodes=[source, target],
            connections=[
                EnergyConnection(
                    source_id=source.get_id(),
                    target_id=target.get_id(),
                )
            ],
        )


def test_rejects_duplicate_node_ids():
    duplicate_id = FuelSource._create_id()

    with pytest.raises(
        ValueError,
        match="Duplicate energy node ID",
    ):
        EnergyNetwork(
            nodes=[
                FuelSource(energy_unit_id=duplicate_id),
                ElectricalLoad(load_mw=5, energy_unit_id=duplicate_id),
            ],
            connections=[],
        )


def test_rejects_cycles():
    first = ElectricalPowerLoss(loss_factor=0.05)
    second = ElectricalPowerLoss(loss_factor=0.05)

    with pytest.raises(
        ValueError,
        match="cannot be cyclic",
    ):
        EnergyNetwork(
            nodes=[first, second],
            connections=[
                EnergyConnection(
                    source_id=first.get_id(),
                    target_id=second.get_id(),
                ),
                EnergyConnection(
                    source_id=second.get_id(),
                    target_id=first.get_id(),
                ),
            ],
        )


def test_supports_fan_out():
    """A provider can supply multiple downstream consumers."""
    source = FuelSource()
    generator = GeneratorSet(max_power_mw=10, fuel_per_mw=5000)
    first_load = ElectricalLoad(
        load_mw=3,
    )
    second_load = ElectricalLoad(load_mw=4)

    network = EnergyNetwork(
        nodes=[
            source,
            generator,
            first_load,
            second_load,
        ],
        connections=[
            EnergyConnection(
                source_id=source.get_id(),
                target_id=generator.get_id(),
            ),
            EnergyConnection(
                source_id=generator.get_id(),
                target_id=first_load.get_id(),
            ),
            EnergyConnection(
                source_id=generator.get_id(),
                target_id=second_load.get_id(),
            ),
        ],
    )

    assert network.successors(generator.get_id()) == frozenset(
        {
            first_load.get_id(),
            second_load.get_id(),
        }
    )
