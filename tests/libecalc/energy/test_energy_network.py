import pytest
from inline_snapshot import snapshot

from libecalc.energy.energy_units import (
    ElectricalBus,
    ElectricalCable,
    ElectricalConsumer,
    ElectricalSource,
    FuelGasSource,
    GeneratorSet,
)
from libecalc.energy.errors import InvalidEnergyNetworkError
from libecalc.energy.network import EnergyConnection, EnergyNetwork


class TestEnergyNetworkValidation:
    def test_rejects_incompatible_energy_types(self):
        source = FuelGasSource(name="source")
        load = ElectricalConsumer(name="load")

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

    def test_rejects_unknown_source(self):
        load = ElectricalConsumer(name="load")
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

    def test_rejects_unknown_target(self):
        source = FuelGasSource(name="source")
        missing_id = ElectricalConsumer._create_id()

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

    @pytest.mark.snapshot
    @pytest.mark.inlinesnapshot
    def test_rejects_consumer_as_source(self):
        source = ElectricalConsumer(name="source")
        target = ElectricalConsumer(name="target")

        with pytest.raises(
            InvalidEnergyNetworkError,
        ) as exc_info:
            EnergyNetwork(
                nodes=[source, target],
                connections=[
                    EnergyConnection(
                        source_id=source.get_id(),
                        target_id=target.get_id(),
                    )
                ],
            )
        assert str(exc_info.value) == snapshot(
            f"Energy domain error: Connection source 'source' ({source.get_id()}) "
            "of type ElectricalConsumer provides no output energy"
        )

    @pytest.mark.snapshot
    @pytest.mark.inlinesnapshot
    def test_rejects_source_as_target(self):
        source = FuelGasSource(name="source")
        target = FuelGasSource(name="target")

        with pytest.raises(
            InvalidEnergyNetworkError,
        ) as exc_info:
            EnergyNetwork(
                nodes=[source, target],
                connections=[
                    EnergyConnection(
                        source_id=source.get_id(),
                        target_id=target.get_id(),
                    )
                ],
            )
        assert str(exc_info.value) == snapshot(
            f"Energy domain error: Connection target 'target' ({target.get_id()}) "
            "of type FuelGasSource accepts no input energy"
        )

    def test_rejects_duplicate_node_ids(self):
        duplicate_id = FuelGasSource._create_id()

        with pytest.raises(
            InvalidEnergyNetworkError,
            match="Duplicate energy node ID",
        ):
            EnergyNetwork(
                nodes=[
                    FuelGasSource(name="source", energy_unit_id=duplicate_id),
                    ElectricalConsumer(name="load", energy_unit_id=duplicate_id),
                ],
                connections=[],
            )

    def test_rejects_cycles(self):
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

    def test_rejects_consumer_without_predecessor(self):
        base_load = ElectricalConsumer("load")
        with pytest.raises(
            InvalidEnergyNetworkError,
            match="requires input energy but has no predecessor",
        ):
            EnergyNetwork(nodes=[base_load], connections=[])

    def test_rejects_transporter_without_predecessor(self):
        """A transporter needs a supply; without one it would deliver energy from nowhere."""
        cable = ElectricalCable("cable", max_power=15)
        load = ElectricalConsumer("load")

        with pytest.raises(
            InvalidEnergyNetworkError,
            match="requires input energy but has no predecessor",
        ):
            EnergyNetwork(
                nodes=[cable, load],
                connections=[EnergyConnection(cable.get_id(), load.get_id())],
            )


class TestEnergyNetworkTopology:
    def test_exposes_nodes_in_topological_order(self):
        source = FuelGasSource(name="source")
        generator = GeneratorSet(
            name="generator", max_power=10, power_to_fuel=lambda output_power: output_power * 5000.0
        )
        load = ElectricalConsumer(name="load")

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
        assert network.get_topological_order() == (
            source.get_id(),
            generator.get_id(),
            load.get_id(),
        )
        assert network.get_node(generator.get_id()) is generator
        assert network.get_nodes() == (source, generator, load)

    def test_connects_provider_to_multiple_consumers(self):
        """A provider can supply multiple downstream consumers."""
        source = FuelGasSource(name="source")
        generator = GeneratorSet(name="generator", max_power=10, power_to_fuel=lambda output_power: output_power * 5000)
        first_load = ElectricalConsumer(name="first_load")
        second_load = ElectricalConsumer(name="second_load")

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

        assert network.get_successors(generator.get_id()) == frozenset(
            {
                first_load.get_id(),
                second_load.get_id(),
            }
        )

    def test_connects_multiple_providers_to_consumer_through_junction(self):
        grid = ElectricalSource(name="grid")
        wind = ElectricalSource(name="wind")

        bus = ElectricalBus(name="bus")
        load = ElectricalConsumer(name="load")

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

        assert network.get_predecessors(bus.get_id()) == frozenset(
            {
                grid.get_id(),
                wind.get_id(),
            }
        )
        assert network.get_successors(bus.get_id()) == frozenset({load.get_id()})

    def test_connects_source_to_consumer_through_transporter(self):
        grid = ElectricalSource(
            name="grid",
        )
        cable = ElectricalCable(
            name="cable",
            max_power=15,
            loss_fraction=0.04,
        )
        load = ElectricalConsumer(name="load")

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

        assert network.get_predecessors(cable.get_id()) == frozenset({grid.get_id()})
        assert network.get_successors(cable.get_id()) == frozenset({load.get_id()})
