from typing import cast

import pytest

from libecalc.energy import ElectricalPower, FuelGasRate, MechanicalPower
from libecalc.energy.dispatch import PriorityDispatch
from libecalc.energy.energy_network_evaluation import EnergyNetworkEvaluation
from libecalc.energy.energy_units import (
    ElectricalBus,
    ElectricalCable,
    ElectricalConsumer,
    ElectricalMotor,
    ElectricalSource,
    FuelGasSource,
    GeneratorSet,
    MechanicalConsumer,
)
from libecalc.energy.errors import (
    EnergyAllocationRequiredError,
    InvalidEnergyNetworkError,
    InvalidEnergyNetworkEvaluationInputError,
)
from libecalc.energy.network import EnergyConnectionId, EnergyNetwork


def create_network(nodes, connections):
    return EnergyNetwork.create(
        node_input_types={node.get_id(): node.get_input_energy_type() for node in nodes},
        node_output_types={node.get_id(): node.get_output_energy_type() for node in nodes},
        connections=connections,
    )


def create_electrical_network():
    source = ElectricalSource("source")
    consumer = ElectricalConsumer("consumer")
    network = create_network(
        nodes=[source, consumer],
        connections=[
            (source.get_id(), consumer.get_id()),
        ],
    )
    return network, source, consumer


class TestEnergyNetworkEvaluationInputValidation:
    def test_rejects_energy_units_with_different_energy_types_than_network(self):
        network, source, consumer = create_electrical_network()
        incompatible_consumer = MechanicalConsumer("consumer", energy_unit_id=consumer.get_id())

        with pytest.raises(
            InvalidEnergyNetworkEvaluationInputError,
            match="energy types that do not match the network",
        ):
            EnergyNetworkEvaluation(
                energy_network=network,
                energy_units=[source, incompatible_consumer],
            )

    def test_rejects_missing_consumer_input_energy(self):
        network, source, consumer = create_electrical_network()

        with pytest.raises(
            InvalidEnergyNetworkEvaluationInputError,
            match=r"Missing connection demands for connections: 'source'.*-> 'consumer'",
        ):
            EnergyNetworkEvaluation(
                energy_network=network,
                energy_units=[source, consumer],
            ).propagate_energy({})

    def test_rejects_consumer_demand_for_non_consumer(self):
        network, source, consumer = create_electrical_network()

        with pytest.raises(
            InvalidEnergyNetworkEvaluationInputError,
            match="Unexpected connection demands for connections",
        ):
            EnergyNetworkEvaluation(
                energy_network=network,
                energy_units=[source, consumer],
            ).propagate_energy(
                {
                    network.get_connection(source.get_id(), consumer.get_id()).id: ElectricalPower(5),
                    cast(EnergyConnectionId, ElectricalSource._create_id()): ElectricalPower(5),
                }
            )

    def test_rejects_wrong_consumer_input_energy_type(self):
        network, source, consumer = create_electrical_network()

        with pytest.raises(
            InvalidEnergyNetworkEvaluationInputError,
            match=r"Consumer demand for connection 'source'.*-> 'consumer'.*requires ElectricalPower",
        ):
            EnergyNetworkEvaluation(
                energy_network=network,
                energy_units=[source, consumer],
            ).propagate_energy(
                {
                    network.get_connection(source.get_id(), consumer.get_id()).id: FuelGasRate(5),
                }
            )


class TestEnergyNetworkEnergyCalculation:
    def test_calculates_input_and_output_energy_through_network(self):
        source = FuelGasSource("source")
        generator = GeneratorSet("generator", max_power=10, power_to_fuel=lambda output: output * 1_000)
        bus = ElectricalBus("bus")
        motor = ElectricalMotor("motor", max_power=10, efficiency=0.8)
        pump = MechanicalConsumer("pump")
        base_load = ElectricalConsumer("base_load")

        network = create_network(
            nodes=[source, generator, bus, motor, pump, base_load],
            connections=[
                (source.get_id(), generator.get_id()),
                (generator.get_id(), bus.get_id()),
                (bus.get_id(), motor.get_id()),
                (motor.get_id(), pump.get_id()),
                (bus.get_id(), base_load.get_id()),
            ],
        )
        evaluation = EnergyNetworkEvaluation(
            energy_network=network,
            energy_units=[source, generator, bus, motor, pump, base_load],
        )
        connection_energy = evaluation.propagate_energy(
            {
                network.get_connection(motor.get_id(), pump.get_id()).id: MechanicalPower(4),
                network.get_connection(bus.get_id(), base_load.get_id()).id: ElectricalPower(5),
            }
        )

        assert connection_energy == {
            network.get_connection(source.get_id(), generator.get_id()).id: FuelGasRate(10_000),
            network.get_connection(generator.get_id(), bus.get_id()).id: ElectricalPower(10),
            network.get_connection(bus.get_id(), motor.get_id()).id: ElectricalPower(5),
            network.get_connection(motor.get_id(), pump.get_id()).id: MechanicalPower(4),
            network.get_connection(bus.get_id(), base_load.get_id()).id: ElectricalPower(5),
        }

    def test_returns_no_connection_energy_for_source_without_successors(self):
        source = FuelGasSource("source")
        network = create_network(nodes=[source], connections=[])
        evaluation = EnergyNetworkEvaluation(
            energy_network=network,
            energy_units=[source],
        )

        assert evaluation.propagate_energy({}) == {}

    def test_calculates_input_energy_for_transporter(self):
        source = ElectricalSource("source")
        cable = ElectricalCable("cable", max_power=10, loss_fraction=0.04)
        consumer = ElectricalConsumer("consumer")

        network = create_network(
            nodes=[source, cable, consumer],
            connections=[
                (source.get_id(), cable.get_id()),
                (cable.get_id(), consumer.get_id()),
            ],
        )

        evaluation = EnergyNetworkEvaluation(
            energy_network=network,
            energy_units=[source, cable, consumer],
        )

        assert evaluation.propagate_energy(
            {network.get_connection(cable.get_id(), consumer.get_id()).id: ElectricalPower(10)}
        ) == {
            network.get_connection(source.get_id(), cable.get_id()).id: ElectricalPower(10 / 0.96),
            network.get_connection(cable.get_id(), consumer.get_id()).id: ElectricalPower(10),
        }


class TestJunctionDispatch:
    def test_dispatches_to_shore_before_genset(self):
        """Power from shore is filled first, and the generator set covers only the shortfall."""
        fuel_source = FuelGasSource("fuel_source")
        grid = ElectricalSource("grid", max_power=5)
        genset = GeneratorSet("genset", max_power=10, power_to_fuel=lambda power: power * 1_000)
        bus = ElectricalBus("bus", dispatch_strategy=PriorityDispatch(order=(grid.get_id(), genset.get_id())))
        load = ElectricalConsumer("load")

        units = [fuel_source, grid, genset, bus, load]
        network = create_network(
            nodes=units,
            connections=[
                (fuel_source.get_id(), genset.get_id()),
                (grid.get_id(), bus.get_id()),
                (genset.get_id(), bus.get_id()),
                (bus.get_id(), load.get_id()),
            ],
        )
        evaluation = EnergyNetworkEvaluation(energy_network=network, energy_units=units)

        energy = evaluation.propagate_energy(
            {network.get_connection(bus.get_id(), load.get_id()).id: ElectricalPower(8)}
        )

        assert energy[network.get_connection(grid.get_id(), bus.get_id()).id] == ElectricalPower(5)
        assert energy[network.get_connection(genset.get_id(), bus.get_id()).id] == ElectricalPower(3)
        assert energy[network.get_connection(fuel_source.get_id(), genset.get_id()).id] == FuelGasRate(3_000)

    def test_separate_genset_curves_reproduce_legacy_fuel_jump(self):
        """Per-generator curves replace the jumps encoded in a single legacy curve."""
        fuel_source = FuelGasSource("fuel_source")
        first = GeneratorSet("first_genset", max_power=10, power_to_fuel=lambda power: power * 1_000)
        second = GeneratorSet("second_genset", max_power=10, power_to_fuel=lambda power: 10_000 + power * 2_000)
        bus = ElectricalBus("bus", dispatch_strategy=PriorityDispatch(order=(first.get_id(), second.get_id())))
        load = ElectricalConsumer("load")

        units = [fuel_source, first, second, bus, load]
        network = create_network(
            nodes=units,
            connections=[
                (fuel_source.get_id(), first.get_id()),
                (fuel_source.get_id(), second.get_id()),
                (first.get_id(), bus.get_id()),
                (second.get_id(), bus.get_id()),
                (bus.get_id(), load.get_id()),
            ],
        )
        evaluation = EnergyNetworkEvaluation(energy_network=network, energy_units=units)

        energy = evaluation.propagate_energy(
            {network.get_connection(bus.get_id(), load.get_id()).id: ElectricalPower(12)}
        )

        assert energy[network.get_connection(first.get_id(), bus.get_id()).id] == ElectricalPower(10)
        assert energy[network.get_connection(second.get_id(), bus.get_id()).id] == ElectricalPower(2)
        assert energy[network.get_connection(fuel_source.get_id(), first.get_id()).id] == FuelGasRate(10_000)
        assert energy[network.get_connection(fuel_source.get_id(), second.get_id()).id] == FuelGasRate(14_000)

    def test_overflows_last_candidate_when_total_capacity_is_insufficient(self):
        """Demand beyond total capacity lands on the last candidate rather than raising."""
        first_grid = ElectricalSource("first_grid", max_power=5)
        second_grid = ElectricalSource("second_grid", max_power=5)
        bus = ElectricalBus(
            "bus", dispatch_strategy=PriorityDispatch(order=(first_grid.get_id(), second_grid.get_id()))
        )
        load = ElectricalConsumer("load")

        units = [first_grid, second_grid, bus, load]
        network = create_network(
            nodes=units,
            connections=[
                (first_grid.get_id(), bus.get_id()),
                (second_grid.get_id(), bus.get_id()),
                (bus.get_id(), load.get_id()),
            ],
        )
        evaluation = EnergyNetworkEvaluation(energy_network=network, energy_units=units)

        energy = evaluation.propagate_energy(
            {network.get_connection(bus.get_id(), load.get_id()).id: ElectricalPower(12)}
        )

        assert energy[network.get_connection(first_grid.get_id(), bus.get_id()).id] == ElectricalPower(5)
        assert energy[network.get_connection(second_grid.get_id(), bus.get_id()).id] == ElectricalPower(7)

    def test_dispatch_uses_cable_capacity_not_upstream_grid_capacity(self):
        """Availability is a candidate's own capacity, not what the chain behind it can deliver."""
        grid = ElectricalSource("grid", max_power=20)
        cable = ElectricalCable("cable", max_power=30)
        wind = ElectricalSource("wind", max_power=10)
        bus = ElectricalBus("bus", dispatch_strategy=PriorityDispatch(order=(cable.get_id(), wind.get_id())))
        load = ElectricalConsumer("load")

        units = [grid, cable, wind, bus, load]
        network = create_network(
            nodes=units,
            connections=[
                (grid.get_id(), cable.get_id()),
                (cable.get_id(), bus.get_id()),
                (wind.get_id(), bus.get_id()),
                (bus.get_id(), load.get_id()),
            ],
        )
        evaluation = EnergyNetworkEvaluation(energy_network=network, energy_units=units)

        energy = evaluation.propagate_energy(
            {network.get_connection(bus.get_id(), load.get_id()).id: ElectricalPower(25)}
        )

        # The cable is filled to its own 30 MW rating, so the 20 MW grid behind it is over-drawn
        # and the 10 MW wind source is left idle.
        assert energy[network.get_connection(cable.get_id(), bus.get_id()).id] == ElectricalPower(25)
        assert energy[network.get_connection(grid.get_id(), cable.get_id()).id] == ElectricalPower(25)
        assert energy[network.get_connection(wind.get_id(), bus.get_id()).id] == ElectricalPower(0)

    def test_requires_dispatch_strategy_for_junction_with_multiple_predecessors(self):
        first_grid = ElectricalSource("first_grid")
        second_grid = ElectricalSource("second_grid")
        bus = ElectricalBus("bus")
        load = ElectricalConsumer("load")

        units = [first_grid, second_grid, bus, load]
        network = create_network(
            nodes=units,
            connections=[
                (first_grid.get_id(), bus.get_id()),
                (second_grid.get_id(), bus.get_id()),
                (bus.get_id(), load.get_id()),
            ],
        )

        with pytest.raises(EnergyAllocationRequiredError, match="requires a dispatch strategy"):
            EnergyNetworkEvaluation(energy_network=network, energy_units=units)

    def test_rejects_multiple_predecessors_for_consumer(self):
        """Two supplies feeding one load must go through a junction that says how to split the demand.

        The YAML schema already enforces this: INPUT is a single reference on a consumer and a list
        only on a junction. Without this check the domain would accept a model the schema forbids,
        and the split would be whatever the caller happened to put on each connection.
        """
        first_grid = ElectricalSource("first_grid")
        second_grid = ElectricalSource("second_grid")
        load = ElectricalConsumer("load")

        units = [first_grid, second_grid, load]
        network = create_network(
            nodes=units,
            connections=[
                (first_grid.get_id(), load.get_id()),
                (second_grid.get_id(), load.get_id()),
            ],
        )

        with pytest.raises(InvalidEnergyNetworkError, match="only junctions support fan-in"):
            EnergyNetworkEvaluation(energy_network=network, energy_units=units)

    def test_rejects_multiple_predecessors_for_converter(self):
        """A converter cannot resolve fan-in either, and reaching _allocate would trip its assertion."""
        first_source = FuelGasSource("first_source")
        second_source = FuelGasSource("second_source")
        generator = GeneratorSet("generator", max_power=10, power_to_fuel=lambda output: output * 1_000)
        load = ElectricalConsumer("load")

        units = [first_source, second_source, generator, load]
        network = create_network(
            nodes=units,
            connections=[
                (first_source.get_id(), generator.get_id()),
                (second_source.get_id(), generator.get_id()),
                (generator.get_id(), load.get_id()),
            ],
        )

        with pytest.raises(InvalidEnergyNetworkError, match="only junctions support fan-in"):
            EnergyNetworkEvaluation(energy_network=network, energy_units=units)

    def test_rejects_dispatch_strategy_candidate_ids_that_do_not_match_predecessors(self):
        first_grid = ElectricalSource("first_grid")
        second_grid = ElectricalSource("second_grid")
        missing_grid = ElectricalSource("missing_grid")
        bus = ElectricalBus(
            "bus", dispatch_strategy=PriorityDispatch(order=(first_grid.get_id(), missing_grid.get_id()))
        )
        load = ElectricalConsumer("load")

        units = [first_grid, second_grid, bus, load]
        network = create_network(
            nodes=units,
            connections=[
                (first_grid.get_id(), bus.get_id()),
                (second_grid.get_id(), bus.get_id()),
                (bus.get_id(), load.get_id()),
            ],
        )

        with pytest.raises(InvalidEnergyNetworkError, match="must match its predecessors"):
            EnergyNetworkEvaluation(energy_network=network, energy_units=units)

    def test_rejects_dispatch_strategy_candidate_ids_for_junction_with_a_single_predecessor(self):
        """A single candidate leaves a strategy nothing to decide, but it must still name that candidate.

        The strategy checks used to sit behind the fan-in test, so a junction with one predecessor had its
        strategy ignored entirely and could name a node it was not connected to without any error.
        """
        grid = ElectricalSource("grid")
        other_grid = ElectricalSource("other_grid")
        bus = ElectricalBus("bus", dispatch_strategy=PriorityDispatch(order=(other_grid.get_id(),)))
        load = ElectricalConsumer("load")
        other_load = ElectricalConsumer("other_load")

        units = [grid, other_grid, bus, load, other_load]
        network = create_network(
            nodes=units,
            connections=[
                (grid.get_id(), bus.get_id()),
                (bus.get_id(), load.get_id()),
                (other_grid.get_id(), other_load.get_id()),
            ],
        )

        with pytest.raises(InvalidEnergyNetworkError, match="must match its predecessors"):
            EnergyNetworkEvaluation(energy_network=network, energy_units=units)

    def test_accepts_dispatch_strategy_naming_the_only_predecessor(self):
        """A degenerate strategy is legal and behaves exactly like an undispatched single supply."""
        grid = ElectricalSource("grid")
        bus = ElectricalBus("bus", dispatch_strategy=PriorityDispatch(order=(grid.get_id(),)))
        first_load = ElectricalConsumer("first_load")
        second_load = ElectricalConsumer("second_load")

        units = [grid, bus, first_load, second_load]
        network = create_network(
            nodes=units,
            connections=[
                (grid.get_id(), bus.get_id()),
                (bus.get_id(), first_load.get_id()),
                (bus.get_id(), second_load.get_id()),
            ],
        )
        evaluation = EnergyNetworkEvaluation(energy_network=network, energy_units=units)

        energy = evaluation.propagate_energy(
            {
                network.get_connection(bus.get_id(), first_load.get_id()).id: ElectricalPower(3),
                network.get_connection(bus.get_id(), second_load.get_id()).id: ElectricalPower(7),
            }
        )

        assert energy[network.get_connection(grid.get_id(), bus.get_id()).id] == ElectricalPower(10)

        first_grid = ElectricalSource("first_grid")
        second_grid = ElectricalSource("second_grid")
        bus = ElectricalBus(
            "bus", dispatch_strategy=PriorityDispatch(order=(first_grid.get_id(), second_grid.get_id()))
        )
        bus_load = ElectricalConsumer("bus_load")
        direct_load = ElectricalConsumer("direct_load")

        units = [first_grid, second_grid, bus, bus_load, direct_load]
        network = create_network(
            nodes=units,
            connections=[
                (first_grid.get_id(), bus.get_id()),
                (first_grid.get_id(), direct_load.get_id()),
                (second_grid.get_id(), bus.get_id()),
                (bus.get_id(), bus_load.get_id()),
            ],
        )

        with pytest.raises(InvalidEnergyNetworkError, match="must have exactly one successor"):
            EnergyNetworkEvaluation(energy_network=network, energy_units=units)
