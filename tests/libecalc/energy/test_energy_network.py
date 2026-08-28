import pytest

from libecalc.energy.energy_units import (
    BaseLoad,
    ElectricalBus,
    ElectricalCable,
    FuelGasSource,
    GeneratorSet,
    OffshoreWind,
    OnshoreGrid,
)
from libecalc.energy.errors import InvalidEnergyNetworkError
from libecalc.energy.network import EnergyConnection, EnergyNetwork


def test_accepts_valid_energy_network():
    source = FuelGasSource(name="source")
    generator = GeneratorSet(name="generator", max_power=10, power_to_fuel=lambda output_power: output_power * 5000.0)
    load = BaseLoad(name="load", load=5)

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
    source = FuelGasSource(name="source")
    load = BaseLoad(name="load", load=5)

    with pytest.raises(
        InvalidEnergyNetworkError,
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
    load = BaseLoad(name="load", load=5)
    missing_id = FuelGasSource._create_id()

    with pytest.raises(InvalidEnergyNetworkError, match="Unknown source"):
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
    source = FuelGasSource(name="source")
    missing_id = BaseLoad._create_id()

    with pytest.raises(InvalidEnergyNetworkError, match="Unknown target"):
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
    source = BaseLoad(name="source", load=5)
    target = BaseLoad(name="target", load=5)

    with pytest.raises(
        InvalidEnergyNetworkError,
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


def test_rejects_source_as_target():
    source = FuelGasSource(name="source")
    target = FuelGasSource(name="target")

    with pytest.raises(
        InvalidEnergyNetworkError,
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
    duplicate_id = FuelGasSource._create_id()

    with pytest.raises(
        InvalidEnergyNetworkError,
        match="Duplicate energy node ID",
    ):
        EnergyNetwork(
            nodes=[
                FuelGasSource(name="source", energy_unit_id=duplicate_id),
                BaseLoad(name="load", load=5, energy_unit_id=duplicate_id),
            ],
            connections=[],
        )


def test_rejects_cycles():
    first = ElectricalBus(name="first")
    second = ElectricalBus(name="second")

    with pytest.raises(
        InvalidEnergyNetworkError,
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


def test_connects_provider_to_multiple_consumers():
    """A provider can supply multiple downstream consumers."""
    source = FuelGasSource(name="source")
    generator = GeneratorSet(name="generator", max_power=10, power_to_fuel=lambda output_power: output_power * 5000)
    first_load = BaseLoad(name="first_load", load=3)
    second_load = BaseLoad(name="second_load", load=4)

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


def test_connects_multiple_providers_to_consumer_through_junction():
    grid = OnshoreGrid(name="grid", max_power=20)
    wind = OffshoreWind(name="wind", power=5)

    bus = ElectricalBus(name="bus")
    load = BaseLoad(name="load", load=10)

    network = EnergyNetwork(
        nodes=[grid, wind, bus, load],
        connections=[
            EnergyConnection(
                source_id=grid.get_id(),
                target_id=bus.get_id(),
            ),
            EnergyConnection(
                source_id=wind.get_id(),
                target_id=bus.get_id(),
            ),
            EnergyConnection(
                source_id=bus.get_id(),
                target_id=load.get_id(),
            ),
        ],
    )

    assert network.predecessors(bus.get_id()) == frozenset(
        {
            grid.get_id(),
            wind.get_id(),
        }
    )
    assert network.successors(bus.get_id()) == frozenset({load.get_id()})


def test_connects_source_to_consumer_through_transporter():
    grid = OnshoreGrid(
        name="grid",
        max_power=20,
    )
    cable = ElectricalCable(
        name="cable",
        max_power=15,
        loss_fraction=0.04,
    )
    load = BaseLoad(name="load", load=10)

    network = EnergyNetwork(
        nodes=[grid, cable, load],
        connections=[
            EnergyConnection(
                source_id=grid.get_id(),
                target_id=cable.get_id(),
            ),
            EnergyConnection(
                source_id=cable.get_id(),
                target_id=load.get_id(),
            ),
        ],
    )

    assert network.predecessors(cable.get_id()) == frozenset({grid.get_id()})
    assert network.successors(cable.get_id()) == frozenset({load.get_id()})
