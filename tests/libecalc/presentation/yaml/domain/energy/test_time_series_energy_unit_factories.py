from datetime import datetime
from functools import partial
from uuid import UUID

import pytest

from libecalc.common.time_utils import Period
from libecalc.ecalc_model.model_event import EnergyUnitEventChangeType, EnergyUnitModelEvent
from libecalc.energy import DieselRate, ElectricalPower, FuelGasRate, MechanicalPower
from libecalc.energy.dispatch import PriorityDispatch
from libecalc.energy.energy_network_topology import EnergyConnection, EnergyConnectionId
from libecalc.energy.energy_unit import EnergyUnitId
from libecalc.energy.errors import InvalidEnergyNetworkInputError
from libecalc.energy.models.generator_fuel_model import GeneratorFuelModel
from libecalc.presentation.yaml.domain.energy import (
    TimeSeriesElectricalCableFactory,
    TimeSeriesElectricalMotorFactory,
    TimeSeriesGasTurbineFactory,
    TimeSeriesGeneratorFactory,
    TimeSeriesJunctionFactory,
    TimeSeriesSourceFactory,
)
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression

FIRST_PERIOD = Period(start=datetime(2020, 1, 1), end=datetime(2021, 1, 1))
SECOND_PERIOD = Period(start=datetime(2021, 1, 1), end=datetime(2022, 1, 1))
THIRD_PERIOD = Period(start=datetime(2022, 1, 1), end=datetime(2023, 1, 1))
FOURTH_PERIOD = Period(start=datetime(2023, 1, 1), end=datetime(2024, 1, 1))
PERIODS = [FIRST_PERIOD, SECOND_PERIOD]

FIRST_CANDIDATE = EnergyUnitId(UUID(int=1))
SECOND_CANDIDATE = EnergyUnitId(UUID(int=2))


class IdentityFuelModel:
    """Fuel model test double whose fuel_for_power is the identity function."""

    def fuel_for_power(self, power: float) -> float:
        return power


def linear_fuel_model(*, fuel_per_power: float, max_power: float = 100) -> GeneratorFuelModel:
    return GeneratorFuelModel(powers=[0, max_power], fuels=[0, fuel_per_power * max_power])


@pytest.fixture
def expression_factory(expression_evaluator_factory):
    def build(expression, variables: dict[str, list[float]] | None = None) -> TimeSeriesExpression:
        evaluator = expression_evaluator_factory.from_periods(periods=PERIODS, variables=variables)
        return TimeSeriesExpression(expression=expression, expression_evaluator=evaluator)

    return build


def incoming(target_id: EnergyUnitId, energy_type, *source_ids: EnergyUnitId) -> tuple[EnergyConnection, ...]:
    return tuple(
        EnergyConnection(
            id=EnergyConnectionId(UUID(int=1000 + index)),
            source_id=source_id,
            target_id=target_id,
            energy_type=energy_type,
        )
        for index, source_id in enumerate(source_ids)
    )


# Capacity is a rating on each unit's output, which for a converter differs from what it draws.
RATED_FACTORIES = [
    pytest.param(TimeSeriesSourceFactory, FuelGasRate, None, id="fuel gas source"),
    pytest.param(TimeSeriesSourceFactory, ElectricalPower, None, id="electrical source"),
    pytest.param(TimeSeriesSourceFactory, DieselRate, None, id="diesel source"),
    pytest.param(
        partial(TimeSeriesGasTurbineFactory, fuel_model=IdentityFuelModel()),
        MechanicalPower,
        FuelGasRate,
        id="gas turbine",
    ),
    pytest.param(TimeSeriesElectricalMotorFactory, MechanicalPower, ElectricalPower, id="electrical motor"),
    pytest.param(TimeSeriesElectricalCableFactory, ElectricalPower, ElectricalPower, id="electrical cable"),
]


class TestRatedFactories:
    @pytest.mark.parametrize(("factory_class", "output_type", "input_type"), RATED_FACTORIES)
    def test_resolves_capacity_per_period_in_the_output_energy_type(
        self, expression_factory, factory_class, output_type, input_type
    ):
        factory = factory_class(name="unit", capacity=expression_factory("SIM1;CAPACITY", {"SIM1;CAPACITY": [5, 8]}))
        connections = () if input_type is None else incoming(factory.get_id(), input_type, FIRST_CANDIDATE)

        first = factory.create(output_type(1), incoming_connections=connections, period=FIRST_PERIOD)
        second = factory.create(output_type(1), incoming_connections=connections, period=SECOND_PERIOD)

        assert first.get_capacity() == output_type(5)
        assert second.get_capacity() == output_type(8)
        assert first.get_input_energies().keys() == {connection.id for connection in connections}

    def test_zero_capacity_is_a_limit(self, expression_factory):
        factory = TimeSeriesSourceFactory(name="grid", capacity=expression_factory(0))

        assert factory.create(ElectricalPower(1), incoming_connections=(), period=FIRST_PERIOD).get_capacity() == (
            ElectricalPower(0)
        )

    def test_unconfigured_source_needs_no_period(self):
        factory = TimeSeriesSourceFactory(name="fuel")

        assert factory.create(FuelGasRate(1), incoming_connections=()).get_capacity() is None

    def test_configured_capacity_requires_a_period(self, expression_factory):
        factory = TimeSeriesSourceFactory(name="grid", capacity=expression_factory(5))

        with pytest.raises(InvalidEnergyNetworkInputError, match="needs a period"):
            factory.create(ElectricalPower(1), incoming_connections=())

    def test_rejects_period_without_a_value(self, expression_factory):
        factory = TimeSeriesSourceFactory(name="grid", capacity=expression_factory(5))
        unknown_period = Period(start=datetime(2030, 1, 1), end=datetime(2031, 1, 1))

        with pytest.raises(InvalidEnergyNetworkInputError, match="has no value for period"):
            factory.create(ElectricalPower(1), incoming_connections=(), period=unknown_period)

    @pytest.mark.parametrize("value", [-1.0, float("nan"), float("inf")])
    def test_rejects_capacity_that_is_not_finite_and_non_negative(self, expression_factory, value):
        factory = TimeSeriesSourceFactory(
            name="grid", capacity=expression_factory("SIM1;CAPACITY", {"SIM1;CAPACITY": [value, value]})
        )

        with pytest.raises(InvalidEnergyNetworkInputError, match="must be finite and non-negative"):
            factory.create(ElectricalPower(1), incoming_connections=(), period=FIRST_PERIOD)


class TestJunctionFactories:
    def test_resolves_input_capacities_per_period(self, expression_factory):
        bus = TimeSeriesJunctionFactory(
            name="bus",
            energy_type=ElectricalPower,
            dispatch_strategy=PriorityDispatch(order=(FIRST_CANDIDATE, SECOND_CANDIDATE)),
            input_capacities={FIRST_CANDIDATE: expression_factory("SIM1;LIMIT", {"SIM1;LIMIT": [4, 7]})},
        )
        connections = incoming(bus.get_id(), ElectricalPower, FIRST_CANDIDATE, SECOND_CANDIDATE)
        first_input, second_input = (connection.id for connection in connections)

        first = bus.create(ElectricalPower(10), incoming_connections=connections, period=FIRST_PERIOD)
        second = bus.create(ElectricalPower(10), incoming_connections=connections, period=SECOND_PERIOD)

        assert first.get_input_energies() == {first_input: ElectricalPower(4), second_input: ElectricalPower(6)}
        assert second.get_input_energies() == {first_input: ElectricalPower(7), second_input: ElectricalPower(3)}

    def test_omitted_input_capacity_leaves_the_candidate_unlimited(self):
        manifold = TimeSeriesJunctionFactory(
            name="manifold",
            energy_type=FuelGasRate,
            dispatch_strategy=PriorityDispatch(order=(FIRST_CANDIDATE, SECOND_CANDIDATE)),
        )
        connections = incoming(manifold.get_id(), FuelGasRate, FIRST_CANDIDATE, SECOND_CANDIDATE)
        first_input, second_input = (connection.id for connection in connections)

        junction = manifold.create(FuelGasRate(900), incoming_connections=connections)

        assert junction.get_input_energies() == {first_input: FuelGasRate(900), second_input: FuelGasRate(0)}

    def test_rejects_input_capacity_that_is_not_finite(self, expression_factory):
        """NaN would otherwise pass through, since only negative values are rejected by the energy types."""
        bus = TimeSeriesJunctionFactory(
            name="bus",
            energy_type=ElectricalPower,
            dispatch_strategy=PriorityDispatch(order=(FIRST_CANDIDATE, SECOND_CANDIDATE)),
            input_capacities={FIRST_CANDIDATE: expression_factory("SIM1;LIMIT", {"SIM1;LIMIT": [float("nan")] * 2})},
        )
        connections = incoming(bus.get_id(), ElectricalPower, FIRST_CANDIDATE, SECOND_CANDIDATE)

        with pytest.raises(InvalidEnergyNetworkInputError, match="must be finite and non-negative"):
            bus.create(ElectricalPower(1), incoming_connections=connections, period=FIRST_PERIOD)


class TestGasTurbineCapacity:
    @pytest.mark.parametrize(("capacity", "expected"), [(6, 6), (10, 10), (0, 0)])
    def test_capacity_is_resolved_from_the_expression(self, expression_factory, capacity, expected):
        factory = TimeSeriesGasTurbineFactory(
            name="turbine",
            fuel_model=IdentityFuelModel(),
            capacity=expression_factory(capacity),
        )
        connections = incoming(factory.get_id(), FuelGasRate, FIRST_CANDIDATE)

        turbine = factory.create(MechanicalPower(1), incoming_connections=connections, period=FIRST_PERIOD)

        assert turbine.get_capacity() == MechanicalPower(expected)


class TestGeneratorModelEvents:
    def _generator_factory(self, *, model_events, max_power: float = 100):
        return TimeSeriesGeneratorFactory(
            name="generator",
            fuel_model=linear_fuel_model(fuel_per_power=1.0, max_power=max_power),
            input_energy_type=FuelGasRate,
            model_events=model_events,
        )

    @staticmethod
    def _upgrade_at(
        change_time, *, fuel_per_power: float = 1.0, max_power: float = 100
    ) -> EnergyUnitModelEvent[GeneratorFuelModel]:
        return EnergyUnitModelEvent(
            change_type=EnergyUnitEventChangeType.REBUNDLE,
            change_time=change_time,
            change_to=linear_fuel_model(fuel_per_power=fuel_per_power, max_power=max_power),
        )

    def test_uses_the_active_fuel_model_per_period(self):
        generator_factory = self._generator_factory(
            model_events=[self._upgrade_at(SECOND_PERIOD.start, fuel_per_power=0.5)]
        )
        connections = incoming(generator_factory.get_id(), FuelGasRate, FIRST_CANDIDATE)
        (connection,) = connections

        generator = generator_factory.create(ElectricalPower(10), incoming_connections=connections, period=FIRST_PERIOD)
        generator_upgraded = generator_factory.create(
            ElectricalPower(10), incoming_connections=connections, period=SECOND_PERIOD
        )

        assert generator.get_input_energies()[connection.id] == FuelGasRate(10)
        assert generator_upgraded.get_input_energies()[connection.id] == FuelGasRate(5)

    def test_uses_the_latest_upgrade_in_effect_for_each_period(self):
        generator_factory = self._generator_factory(
            model_events=[
                self._upgrade_at(THIRD_PERIOD.start, fuel_per_power=0.25),
                self._upgrade_at(SECOND_PERIOD.start, fuel_per_power=0.5),
            ]
        )
        connections = incoming(generator_factory.get_id(), FuelGasRate, FIRST_CANDIDATE)
        (connection,) = connections

        generator = generator_factory.create(ElectricalPower(8), incoming_connections=connections, period=FIRST_PERIOD)
        generator_first_upgrade = generator_factory.create(
            ElectricalPower(8), incoming_connections=connections, period=SECOND_PERIOD
        )
        generator_second_upgrade = generator_factory.create(
            ElectricalPower(8), incoming_connections=connections, period=THIRD_PERIOD
        )
        generator_carried_forward = generator_factory.create(
            ElectricalPower(8), incoming_connections=connections, period=FOURTH_PERIOD
        )

        assert generator.get_input_energies()[connection.id] == FuelGasRate(8)
        assert generator_first_upgrade.get_input_energies()[connection.id] == FuelGasRate(4)
        assert generator_second_upgrade.get_input_energies()[connection.id] == FuelGasRate(2)
        assert generator_carried_forward.get_input_energies()[connection.id] == FuelGasRate(2)

    def test_capacity_is_the_max_power_of_the_active_fuel_model(self):
        generator_factory = self._generator_factory(
            max_power=10, model_events=[self._upgrade_at(SECOND_PERIOD.start, max_power=15)]
        )
        connections = incoming(generator_factory.get_id(), FuelGasRate, FIRST_CANDIDATE)

        generator = generator_factory.create(ElectricalPower(5), incoming_connections=connections, period=FIRST_PERIOD)
        generator_upgraded = generator_factory.create(
            ElectricalPower(5), incoming_connections=connections, period=SECOND_PERIOD
        )

        assert generator.get_capacity() == ElectricalPower(10)
        assert generator_upgraded.get_capacity() == ElectricalPower(15)

    def test_model_events_are_exposed_in_chronological_order(self):
        later_upgrade = self._upgrade_at(THIRD_PERIOD.start, fuel_per_power=0.25)
        earlier_upgrade = self._upgrade_at(SECOND_PERIOD.start, fuel_per_power=0.5)
        generator_factory = self._generator_factory(model_events=[later_upgrade, earlier_upgrade])

        assert generator_factory.model_events == (earlier_upgrade, later_upgrade)

    def test_model_events_require_a_period(self):
        generator_factory = self._generator_factory(
            model_events=[self._upgrade_at(SECOND_PERIOD.start, fuel_per_power=0.5)]
        )
        connections = incoming(generator_factory.get_id(), FuelGasRate, FIRST_CANDIDATE)

        with pytest.raises(InvalidEnergyNetworkInputError, match="changes model over time"):
            generator_factory.create(ElectricalPower(10), incoming_connections=connections)

    def test_without_events_the_base_model_is_used_without_a_period(self):
        generator_factory = self._generator_factory(model_events=())
        connections = incoming(generator_factory.get_id(), FuelGasRate, FIRST_CANDIDATE)
        (connection,) = connections

        generator = generator_factory.create(ElectricalPower(10), incoming_connections=connections)

        assert generator.get_input_energies()[connection.id] == FuelGasRate(10)
