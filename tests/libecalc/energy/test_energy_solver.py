import pytest

from libecalc.energy import ElectricalPower, FuelGasRate, MechanicalPower
from libecalc.energy.energy_units import (
    BaseLoad,
    ElectricalBus,
    ElectricalMotor,
    FuelGasSource,
    GeneratorSet,
    OffshoreWind,
    OnshoreGrid,
    Pump,
)
from libecalc.energy.errors import EnergySolverError
from libecalc.energy.network import EnergyConnection, EnergyNetwork
from libecalc.energy.solver import EnergySolver, EnergyUnitResult


def test_calculates_input_and_output_energy_through_network():
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

    result = EnergySolver().solve(network)

    # All providers can supply their calculated output energy.
    assert result.is_feasible()

    # The pump has 4 MW of mechanical input and no output energy.
    assert result.get_unit_result(pump.get_id()) == EnergyUnitResult(
        energy_unit_id=pump.get_id(),
        input_energy=MechanicalPower(4),
        output_energy=None,
        capacity_exceeded=False,
    )

    # The base load has 5 MW of electrical input and no output energy.
    assert result.get_unit_result(base_load.get_id()) == EnergyUnitResult(
        energy_unit_id=base_load.get_id(),
        input_energy=ElectricalPower(5),
        output_energy=None,
        capacity_exceeded=False,
    )

    # The motor outputs 4 MW mechanical from 5 MW electrical input.
    assert result.get_unit_result(motor.get_id()) == EnergyUnitResult(
        energy_unit_id=motor.get_id(),
        input_energy=ElectricalPower(5),
        output_energy=MechanicalPower(4),
        capacity_exceeded=False,
    )

    # The bus passes through 10 MW for the motor and base load.
    assert result.get_unit_result(bus.get_id()) == EnergyUnitResult(
        energy_unit_id=bus.get_id(),
        input_energy=ElectricalPower(10),
        output_energy=ElectricalPower(10),
        capacity_exceeded=False,
    )

    # The generator outputs 10 MW from 10,000 Sm3/day of fuel-gas input.
    assert result.get_unit_result(generator.get_id()) == EnergyUnitResult(
        energy_unit_id=generator.get_id(),
        input_energy=FuelGasRate(10_000),
        output_energy=ElectricalPower(10),
        capacity_exceeded=False,
    )

    # The source supplies the generator's total fuel-gas input.
    assert result.get_unit_result(source.get_id()) == EnergyUnitResult(
        energy_unit_id=source.get_id(),
        input_energy=None,
        output_energy=FuelGasRate(10_000),
        capacity_exceeded=False,
    )


def test_reports_capacity_exceeded_without_capping_output_energy():
    source = FuelGasSource("source")
    generator = GeneratorSet(
        "generator",
        max_power=5,
        power_to_fuel=lambda power: power * 1_000,
    )
    load = BaseLoad("load", load=6)
    network = EnergyNetwork(
        nodes=[source, generator, load],
        connections=[
            EnergyConnection(source.get_id(), generator.get_id()),
            EnergyConnection(generator.get_id(), load.get_id()),
        ],
    )

    result = EnergySolver().solve(network)
    generator_result = result.get_unit_result(generator.get_id())

    assert not result.is_feasible()
    assert generator_result.input_energy == FuelGasRate(6_000)
    assert generator_result.output_energy == ElectricalPower(6)
    assert generator_result.capacity_exceeded


def test_raises_for_input_energy_without_predecessor():
    load = BaseLoad("load", load=1)
    network = EnergyNetwork(nodes=[load], connections=[])

    with pytest.raises(EnergySolverError, match="has no predecessor"):
        EnergySolver().solve(network)


def test_raises_when_multiple_predecessors_require_allocation():
    grid = OnshoreGrid("grid", max_power=20)
    wind = OffshoreWind("wind", power=5)
    bus = ElectricalBus("bus")
    load = BaseLoad("load", load=10)
    network = EnergyNetwork(
        nodes=[grid, wind, bus, load],
        connections=[
            EnergyConnection(grid.get_id(), bus.get_id()),
            EnergyConnection(wind.get_id(), bus.get_id()),
            EnergyConnection(bus.get_id(), load.get_id()),
        ],
    )

    with pytest.raises(EnergySolverError, match="multiple predecessors"):
        EnergySolver().solve(network)
