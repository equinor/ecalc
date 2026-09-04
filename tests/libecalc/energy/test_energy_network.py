import pytest
from inline_snapshot import snapshot

from libecalc.energy import ElectricalPower, FuelGasRate, MechanicalPower
from libecalc.energy.dispatch import PriorityDispatch
from libecalc.energy.energy_units import (
    BaseLoad,
    Compressor,
    ElectricalBus,
    ElectricalCable,
    ElectricalMotor,
    FuelGasSource,
    GasTurbine,
    GeneratorSet,
    OffshoreWind,
    OnshoreGrid,
    Pump,
    Shaft,
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

    @pytest.mark.snapshot
    @pytest.mark.inlinesnapshot
    def test_rejects_consumer_as_source(self):
        source = BaseLoad(name="source", load=5)
        target = BaseLoad(name="target", load=5)

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
            f"Energy domain error: Source node of type 'BaseLoad' with id '{source.get_id()}' provides no energy"
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
            f"Energy domain error: Target node of type 'FuelGasSource' with id '{target.get_id()}' requires no energy"
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

    def test_rejects_too_many_predecessors_for_shaft(self):
        fuel_source = FuelGasSource("fg")
        first_turbine = GasTurbine("t1", max_power=25.0, power_to_fuel=lambda mw: mw * 3500)
        second_turbine = GasTurbine("t2", max_power=25.0, power_to_fuel=lambda mw: mw * 3500)
        shaft = Shaft("shaft")
        compressor = Compressor("comp", power=10)

        with pytest.raises(
            InvalidEnergyNetworkError,
            match="allows at most 1 predecessor",
        ):
            EnergyNetwork(
                nodes=[fuel_source, first_turbine, second_turbine, shaft, compressor],
                connections=[
                    EnergyConnection(source_id=fuel_source.get_id(), target_id=first_turbine.get_id()),
                    EnergyConnection(source_id=fuel_source.get_id(), target_id=second_turbine.get_id()),
                    EnergyConnection(source_id=first_turbine.get_id(), target_id=shaft.get_id()),
                    EnergyConnection(source_id=second_turbine.get_id(), target_id=shaft.get_id()),
                    EnergyConnection(source_id=shaft.get_id(), target_id=compressor.get_id()),
                ],
            )

    @pytest.mark.parametrize("load", [0, 10])
    def test_rejects_fan_in_into_consumer(self, load: float):
        first_grid = OnshoreGrid("first_grid", max_power=20)
        second_grid = OnshoreGrid("second_grid", max_power=20)
        consumer = BaseLoad("load", load=load)

        with pytest.raises(InvalidEnergyNetworkError, match="only junctions support fan-in"):
            EnergyNetwork(
                nodes=[first_grid, second_grid, consumer],
                connections=[
                    EnergyConnection(first_grid.get_id(), consumer.get_id()),
                    EnergyConnection(second_grid.get_id(), consumer.get_id()),
                ],
            )

    def test_requires_dispatch_strategy_for_junction_with_multiple_predecessors(self):
        first_grid = OnshoreGrid("first_grid", max_power=20)
        second_grid = OnshoreGrid("second_grid", max_power=20)
        bus = ElectricalBus("bus")
        load = BaseLoad("load", load=10)

        with pytest.raises(EnergyAllocationRequiredError, match="requires a dispatch strategy"):
            EnergyNetwork(
                nodes=[first_grid, second_grid, bus, load],
                connections=[
                    EnergyConnection(first_grid.get_id(), bus.get_id()),
                    EnergyConnection(second_grid.get_id(), bus.get_id()),
                    EnergyConnection(bus.get_id(), load.get_id()),
                ],
            )

    def test_rejects_dispatch_strategy_provider_ids_that_do_not_match_predecessors(self):
        first_grid = OnshoreGrid("first_grid", max_power=20)
        second_grid = OnshoreGrid("second_grid", max_power=20)
        missing_grid = OnshoreGrid("missing_grid", max_power=20)
        bus = ElectricalBus(
            "bus",
            dispatch_strategy=PriorityDispatch(order=(first_grid.get_id(), missing_grid.get_id())),
        )
        load = BaseLoad("load", load=10)

        with pytest.raises(InvalidEnergyNetworkError, match="must match its predecessors"):
            EnergyNetwork(
                nodes=[first_grid, second_grid, bus, load],
                connections=[
                    EnergyConnection(first_grid.get_id(), bus.get_id()),
                    EnergyConnection(second_grid.get_id(), bus.get_id()),
                    EnergyConnection(bus.get_id(), load.get_id()),
                ],
            )

    def test_rejects_provider_shared_by_dispatched_junction_and_another_successor(self):
        first_grid = OnshoreGrid("first_grid", max_power=20)
        second_grid = OnshoreGrid("second_grid", max_power=20)
        bus = ElectricalBus(
            "bus",
            dispatch_strategy=PriorityDispatch(order=(first_grid.get_id(), second_grid.get_id())),
        )
        bus_load = BaseLoad("bus_load", load=10)
        direct_load = BaseLoad("direct_load", load=2)

        with pytest.raises(InvalidEnergyNetworkError, match="must have exactly one successor"):
            EnergyNetwork(
                nodes=[first_grid, second_grid, bus, bus_load, direct_load],
                connections=[
                    EnergyConnection(first_grid.get_id(), bus.get_id()),
                    EnergyConnection(first_grid.get_id(), direct_load.get_id()),
                    EnergyConnection(second_grid.get_id(), bus.get_id()),
                    EnergyConnection(bus.get_id(), bus_load.get_id()),
                ],
            )


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

        assert network.get_successors(generator.get_id()) == frozenset(
            {
                first_load.get_id(),
                second_load.get_id(),
            }
        )

    def test_connects_multiple_providers_to_consumer_through_junction(self):
        grid = OnshoreGrid(name="grid", max_power=20)
        wind = OffshoreWind(name="wind", power=5)

        bus = ElectricalBus(
            name="bus",
            dispatch_strategy=PriorityDispatch(order=(grid.get_id(), wind.get_id())),
        )
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

        assert network.get_predecessors(bus.get_id()) == frozenset(
            {
                grid.get_id(),
                wind.get_id(),
            }
        )
        assert network.get_successors(bus.get_id()) == frozenset({load.get_id()})

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

        assert network.get_predecessors(cable.get_id()) == frozenset({grid.get_id()})
        assert network.get_successors(cable.get_id()) == frozenset({load.get_id()})


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

    def test_dispatches_to_shore_before_genset(self):
        fuel_source = FuelGasSource("fuel_source")
        grid = OnshoreGrid("grid", max_power=5)
        genset = GeneratorSet("genset", max_power=10, power_to_fuel=lambda power: power * 1_000)
        bus = ElectricalBus(
            "bus",
            dispatch_strategy=PriorityDispatch(order=(grid.get_id(), genset.get_id())),
        )
        load = BaseLoad("load", load=8)

        network = EnergyNetwork(
            nodes=[fuel_source, grid, genset, bus, load],
            connections=[
                EnergyConnection(fuel_source.get_id(), genset.get_id()),
                EnergyConnection(grid.get_id(), bus.get_id()),
                EnergyConnection(genset.get_id(), bus.get_id()),
                EnergyConnection(bus.get_id(), load.get_id()),
            ],
        )

        assert network.get_output_energy(grid.get_id()) == ElectricalPower(5)
        assert network.get_output_energy(genset.get_id()) == ElectricalPower(3)
        assert network.get_input_energy(genset.get_id()) == FuelGasRate(3_000)
        assert network.get_output_energy(fuel_source.get_id()) == FuelGasRate(3_000)
        assert network.is_feasible()

    def test_separate_genset_curves_reproduce_legacy_fuel_jump(self):
        fuel_source = FuelGasSource("fuel_source")
        first_genset = GeneratorSet("first_genset", max_power=10, power_to_fuel=lambda power: power * 1_000)
        second_genset = GeneratorSet(
            "second_genset",
            max_power=10,
            power_to_fuel=lambda power: 10_000 + power * 2_000,
        )
        bus = ElectricalBus(
            "bus",
            dispatch_strategy=PriorityDispatch(order=(first_genset.get_id(), second_genset.get_id())),
        )
        load = BaseLoad("load", load=12)

        network = EnergyNetwork(
            nodes=[fuel_source, first_genset, second_genset, bus, load],
            connections=[
                EnergyConnection(fuel_source.get_id(), first_genset.get_id()),
                EnergyConnection(fuel_source.get_id(), second_genset.get_id()),
                EnergyConnection(first_genset.get_id(), bus.get_id()),
                EnergyConnection(second_genset.get_id(), bus.get_id()),
                EnergyConnection(bus.get_id(), load.get_id()),
            ],
        )

        assert network.get_output_energy(first_genset.get_id()) == ElectricalPower(10)
        assert network.get_output_energy(second_genset.get_id()) == ElectricalPower(2)
        assert network.get_output_energy(fuel_source.get_id()) == FuelGasRate(24_000)

    def test_conserves_energy_across_dispatched_junction(self):
        first_grid = OnshoreGrid("first_grid", max_power=5)
        second_grid = OnshoreGrid("second_grid", max_power=10)
        bus = ElectricalBus(
            "bus",
            dispatch_strategy=PriorityDispatch(order=(first_grid.get_id(), second_grid.get_id())),
        )
        load = BaseLoad("load", load=8)

        network = EnergyNetwork(
            nodes=[first_grid, second_grid, bus, load],
            connections=[
                EnergyConnection(first_grid.get_id(), bus.get_id()),
                EnergyConnection(second_grid.get_id(), bus.get_id()),
                EnergyConnection(bus.get_id(), load.get_id()),
            ],
        )

        first_output = network.get_output_energy(first_grid.get_id())
        second_output = network.get_output_energy(second_grid.get_id())
        assert isinstance(first_output, ElectricalPower)
        assert isinstance(second_output, ElectricalPower)
        predecessor_output = first_output + second_output
        assert network.get_input_energy(bus.get_id()) == predecessor_output

    def test_overflows_last_provider_when_total_capacity_is_insufficient(self):
        first_grid = OnshoreGrid("first_grid", max_power=5)
        second_grid = OnshoreGrid("second_grid", max_power=5)
        bus = ElectricalBus(
            "bus",
            dispatch_strategy=PriorityDispatch(order=(first_grid.get_id(), second_grid.get_id())),
        )
        load = BaseLoad("load", load=12)

        network = EnergyNetwork(
            nodes=[first_grid, second_grid, bus, load],
            connections=[
                EnergyConnection(first_grid.get_id(), bus.get_id()),
                EnergyConnection(second_grid.get_id(), bus.get_id()),
                EnergyConnection(bus.get_id(), load.get_id()),
            ],
        )

        assert network.get_output_energy(first_grid.get_id()) == ElectricalPower(5)
        assert network.get_output_energy(second_grid.get_id()) == ElectricalPower(7)
        assert network.is_capacity_exceeded(second_grid.get_id())
        assert not network.is_feasible()

    def test_dispatch_uses_cable_capacity_not_upstream_grid_capacity(self):
        grid = OnshoreGrid("grid", max_power=20)
        cable = ElectricalCable("cable", max_power=30)
        wind = OffshoreWind("wind", power=10)
        bus = ElectricalBus(
            "bus",
            dispatch_strategy=PriorityDispatch(order=(cable.get_id(), wind.get_id())),
        )
        load = BaseLoad("load", load=25)

        network = EnergyNetwork(
            nodes=[grid, cable, wind, bus, load],
            connections=[
                EnergyConnection(grid.get_id(), cable.get_id()),
                EnergyConnection(cable.get_id(), bus.get_id()),
                EnergyConnection(wind.get_id(), bus.get_id()),
                EnergyConnection(bus.get_id(), load.get_id()),
            ],
        )

        assert network.get_output_energy(cable.get_id()) == ElectricalPower(25)
        assert network.get_output_energy(grid.get_id()) == ElectricalPower(25)
        assert network.is_capacity_exceeded(grid.get_id())
        assert not network.is_feasible()

    def test_calculates_shipped_cable_wind_bus_heating_shape_with_loss(self):
        power_from_shore = OnshoreGrid("power_from_shore", max_power=20)
        subsea_cable = ElectricalCable("subsea_cable", max_power=20, loss_fraction=0.03)
        wind_turbine = OffshoreWind("wind_turbine", power=4.4)
        electrical_bus = ElectricalBus(
            "electrical_bus",
            dispatch_strategy=PriorityDispatch(order=(subsea_cable.get_id(), wind_turbine.get_id())),
        )
        heating = BaseLoad("heating", load=10)

        network = EnergyNetwork(
            nodes=[power_from_shore, subsea_cable, wind_turbine, electrical_bus, heating],
            connections=[
                EnergyConnection(power_from_shore.get_id(), subsea_cable.get_id()),
                EnergyConnection(subsea_cable.get_id(), electrical_bus.get_id()),
                EnergyConnection(wind_turbine.get_id(), electrical_bus.get_id()),
                EnergyConnection(electrical_bus.get_id(), heating.get_id()),
            ],
        )

        assert network.get_output_energy(subsea_cable.get_id()) == ElectricalPower(10)
        cable_input = network.get_input_energy(subsea_cable.get_id())
        shore_output = network.get_output_energy(power_from_shore.get_id())
        assert isinstance(cable_input, ElectricalPower)
        assert isinstance(shore_output, ElectricalPower)
        assert cable_input.value == pytest.approx(10 / 0.97)
        assert shore_output.value == pytest.approx(10 / 0.97)
        assert network.get_output_energy(wind_turbine.get_id()) == ElectricalPower(0)
        assert network.is_feasible()


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
