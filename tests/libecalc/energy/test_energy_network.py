import pytest

from libecalc.energy import ElectricalPower, FuelGasRate, MechanicalPower
from libecalc.energy.energy_units import (
    BaseLoad,
    ElectricalBus,
    ElectricalCable,
    ElectricalMotor,
    FuelGasSource,
    GeneratorSet,
    OffshoreWind,
    OnshoreGrid,
    Pump,
)
from libecalc.energy.errors import EnergyAllocationRequiredError, InvalidEnergyNetworkError
from libecalc.energy.network import EnergyConnection, EnergyNetwork


class TestEnergyNetworkValidation:
    def test_rejects_incompatible_energy_types(self):
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

    def test_rejects_unknown_source(self):
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

    def test_rejects_unknown_target(self):
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

    def test_rejects_consumer_as_source(self):
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

    def test_rejects_source_as_target(self):
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

    def test_rejects_duplicate_node_ids(self):
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
        base_load = BaseLoad("load", load=1)
        with pytest.raises(
            InvalidEnergyNetworkError,
            match="requires input energy but has no predecessor",
        ):
            EnergyNetwork(nodes=[base_load], connections=[])


class TestEnergyNetworkTopology:
    def test_exposes_nodes_in_topological_order(self):
        source = FuelGasSource(name="source")
        generator = GeneratorSet(
            name="generator", max_power=10, power_to_fuel=lambda output_power: output_power * 5000.0
        )
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
        assert network.get_node(generator.get_id()) is generator
        assert network.get_nodes() == (source, generator, load)

    def test_connects_provider_to_multiple_consumers(self):
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

    def test_connects_multiple_providers_to_consumer_through_junction(self):
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

    def test_connects_source_to_consumer_through_transporter(self):
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


class TestEnergyNetworkEnergyCalculation:
    def test_calculates_input_and_output_energy_through_network(self):
        source = FuelGasSource("source")
        generator = GeneratorSet(
            "generator",
            max_power=12,
            power_to_fuel=lambda power: power * 1_000,
        )
        bus = ElectricalBus("bus")
        motor = ElectricalMotor("motor", max_power=5, efficiency=0.8)
        pump = Pump("pump", power=4)
        base_load = BaseLoad("base_load", load=5)

        network = EnergyNetwork(
            nodes=[source, generator, bus, motor, pump, base_load],
            connections=[
                EnergyConnection(source.get_id(), generator.get_id()),
                EnergyConnection(generator.get_id(), bus.get_id()),
                EnergyConnection(bus.get_id(), motor.get_id()),
                EnergyConnection(motor.get_id(), pump.get_id()),
                EnergyConnection(bus.get_id(), base_load.get_id()),
            ],
        )

        # The pump has 4 MW of mechanical input and no output energy.
        assert network.get_input_energy(pump.get_id()) == MechanicalPower(4)
        assert network.get_output_energy(pump.get_id()) is None

        # The base load has 5 MW of electrical input and no output energy.
        assert network.get_input_energy(base_load.get_id()) == ElectricalPower(5)
        assert network.get_output_energy(base_load.get_id()) is None

        # The motor outputs 4 MW mechanical from 5 MW electrical input.
        assert network.get_input_energy(motor.get_id()) == ElectricalPower(5)
        assert network.get_output_energy(motor.get_id()) == MechanicalPower(4)

        # The bus passes through 10 MW for the motor and base load.
        assert network.get_input_energy(bus.get_id()) == ElectricalPower(10)
        assert network.get_output_energy(bus.get_id()) == ElectricalPower(10)

        # The generator outputs 10 MW from 10,000 Sm3/day of fuel-gas input.
        assert network.get_input_energy(generator.get_id()) == FuelGasRate(10_000)
        assert network.get_output_energy(generator.get_id()) == ElectricalPower(10)

        # The source supplies the generator's total fuel-gas input.
        assert network.get_input_energy(source.get_id()) is None
        assert network.get_output_energy(source.get_id()) == FuelGasRate(10_000)

    def test_returns_typed_zero_output_for_source_without_successors(self):
        source = FuelGasSource("source")
        network = EnergyNetwork(nodes=[source], connections=[])

        assert network.get_output_energy(source.get_id()) == FuelGasRate(0)

    def test_requires_allocation_for_multiple_predecessors(self):
        first_grid = OnshoreGrid("first_grid", max_power=20)
        second_grid = OnshoreGrid("second_grid", max_power=20)
        load = BaseLoad("load", load=10)

        network = EnergyNetwork(
            nodes=[first_grid, second_grid, load],
            connections=[
                EnergyConnection(first_grid.get_id(), load.get_id()),
                EnergyConnection(second_grid.get_id(), load.get_id()),
            ],
        )

        with pytest.raises(
            EnergyAllocationRequiredError,
            match="allocation strategy is required",
        ):
            network.get_output_energy(first_grid.get_id())

    def test_does_not_require_allocation_for_zero_energy(self):
        first_grid = OnshoreGrid("first_grid", max_power=20)
        second_grid = OnshoreGrid("second_grid", max_power=20)
        load = BaseLoad("load", load=0)

        network = EnergyNetwork(
            nodes=[first_grid, second_grid, load],
            connections=[
                EnergyConnection(first_grid.get_id(), load.get_id()),
                EnergyConnection(second_grid.get_id(), load.get_id()),
            ],
        )

        assert network.get_output_energy(first_grid.get_id()) == ElectricalPower(0)


class TestEnergyNetworkFeasibility:
    def test_reports_capacity_exceeded_without_capping_output_energy(self):
        grid = OnshoreGrid("grid", max_power=5)
        load = BaseLoad("load", load=6)

        network = EnergyNetwork(
            nodes=[grid, load],
            connections=[
                EnergyConnection(grid.get_id(), load.get_id()),
            ],
        )

        assert network.get_capacity(grid.get_id()) == ElectricalPower(5)
        assert network.get_output_energy(grid.get_id()) == ElectricalPower(6)
        assert network.is_capacity_exceeded(grid.get_id())
        assert not network.is_feasible()

    def test_capacity_equal_to_output_energy_is_feasible(self):
        grid = OnshoreGrid("grid", max_power=5)
        load = BaseLoad("load", load=5)

        network = EnergyNetwork(
            nodes=[grid, load],
            connections=[
                EnergyConnection(grid.get_id(), load.get_id()),
            ],
        )

        assert not network.is_capacity_exceeded(grid.get_id())
        assert network.is_feasible()
