from datetime import datetime
from uuid import UUID

import pytest

from libecalc.common.time_utils import Period
from libecalc.energy import DieselRate, ElectricalPower, FuelGasRate, MechanicalPower
from libecalc.energy.dispatch import PriorityDispatch
from libecalc.energy.energy_network_topology import EnergyConnection, EnergyConnectionId
from libecalc.energy.energy_unit import EnergyUnitId
from libecalc.energy.energy_units import ElectricalBus, FuelGasManifold
from libecalc.energy.errors import InvalidEnergyNetworkInputError
from libecalc.presentation.yaml.domain.energy import (
    TimeSeriesElectricalCableFactory,
    TimeSeriesElectricalMotorFactory,
    TimeSeriesGasTurbineFactory,
    TimeSeriesGeneratorSetFactory,
    TimeSeriesJunctionFactory,
    TimeSeriesSourceFactory,
)
from libecalc.presentation.yaml.domain.time_series_expression import TimeSeriesExpression

FIRST_PERIOD = Period(start=datetime(2020, 1, 1), end=datetime(2021, 1, 1))
SECOND_PERIOD = Period(start=datetime(2021, 1, 1), end=datetime(2022, 1, 1))
PERIODS = [FIRST_PERIOD, SECOND_PERIOD]

FIRST_CANDIDATE = EnergyUnitId(UUID(int=1))
SECOND_CANDIDATE = EnergyUnitId(UUID(int=2))


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
    pytest.param(TimeSeriesGeneratorSetFactory, ElectricalPower, FuelGasRate, id="generator set"),
    pytest.param(TimeSeriesGasTurbineFactory, MechanicalPower, FuelGasRate, id="gas turbine"),
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
            junction_class=ElectricalBus,
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
            junction_class=FuelGasManifold,
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
            junction_class=ElectricalBus,
            dispatch_strategy=PriorityDispatch(order=(FIRST_CANDIDATE, SECOND_CANDIDATE)),
            input_capacities={FIRST_CANDIDATE: expression_factory("SIM1;LIMIT", {"SIM1;LIMIT": [float("nan")] * 2})},
        )
        connections = incoming(bus.get_id(), ElectricalPower, FIRST_CANDIDATE, SECOND_CANDIDATE)

        with pytest.raises(InvalidEnergyNetworkInputError, match="must be finite and non-negative"):
            bus.create(ElectricalPower(1), incoming_connections=connections, period=FIRST_PERIOD)
