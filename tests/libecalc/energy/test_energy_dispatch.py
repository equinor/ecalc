from uuid import UUID

import pytest

from libecalc.energy.dispatch import PriorityDispatch, ProviderAvailability
from libecalc.energy.energy_types import ElectricalPower
from libecalc.energy.energy_unit import EnergyUnitId
from libecalc.energy.errors import InvalidDispatchError

FIRST_PROVIDER = EnergyUnitId(UUID(int=1))
SECOND_PROVIDER = EnergyUnitId(UUID(int=2))
THIRD_PROVIDER = EnergyUnitId(UUID(int=3))


def test_exact_fit():
    strategy = PriorityDispatch(order=(FIRST_PROVIDER, SECOND_PROVIDER))
    candidates = (
        ProviderAvailability(provider_id=FIRST_PROVIDER, available=ElectricalPower(5)),
        ProviderAvailability(provider_id=SECOND_PROVIDER, available=ElectricalPower(5)),
    )

    assert strategy.allocate(ElectricalPower(10), candidates) == {
        FIRST_PROVIDER: ElectricalPower(5),
        SECOND_PROVIDER: ElectricalPower(5),
    }


def test_spills_to_second_and_third_provider():
    strategy = PriorityDispatch(order=(FIRST_PROVIDER, SECOND_PROVIDER, THIRD_PROVIDER))
    candidates = (
        ProviderAvailability(provider_id=FIRST_PROVIDER, available=ElectricalPower(5)),
        ProviderAvailability(provider_id=SECOND_PROVIDER, available=ElectricalPower(4)),
        ProviderAvailability(provider_id=THIRD_PROVIDER, available=ElectricalPower(10)),
    )

    assert strategy.allocate(ElectricalPower(12), candidates) == {
        FIRST_PROVIDER: ElectricalPower(5),
        SECOND_PROVIDER: ElectricalPower(4),
        THIRD_PROVIDER: ElectricalPower(3),
    }


def test_reversing_order_changes_allocation():
    candidates = (
        ProviderAvailability(provider_id=FIRST_PROVIDER, available=ElectricalPower(10)),
        ProviderAvailability(provider_id=SECOND_PROVIDER, available=ElectricalPower(10)),
    )

    first_priority = PriorityDispatch(order=(FIRST_PROVIDER, SECOND_PROVIDER)).allocate(ElectricalPower(6), candidates)
    second_priority = PriorityDispatch(order=(SECOND_PROVIDER, FIRST_PROVIDER)).allocate(ElectricalPower(6), candidates)

    assert first_priority == {
        FIRST_PROVIDER: ElectricalPower(6),
        SECOND_PROVIDER: ElectricalPower(0),
    }
    assert second_priority == {
        FIRST_PROVIDER: ElectricalPower(0),
        SECOND_PROVIDER: ElectricalPower(6),
    }


def test_unlimited_first_provider_starves_remaining_providers():
    strategy = PriorityDispatch(order=(FIRST_PROVIDER, SECOND_PROVIDER, THIRD_PROVIDER))
    candidates = (
        ProviderAvailability(provider_id=FIRST_PROVIDER, available=None),
        ProviderAvailability(provider_id=SECOND_PROVIDER, available=ElectricalPower(5)),
        ProviderAvailability(provider_id=THIRD_PROVIDER, available=ElectricalPower(5)),
    )

    assert strategy.allocate(ElectricalPower(12), candidates) == {
        FIRST_PROVIDER: ElectricalPower(12),
        SECOND_PROVIDER: ElectricalPower(0),
        THIRD_PROVIDER: ElectricalPower(0),
    }


def test_insufficient_capacity_overflows_on_last_provider():
    strategy = PriorityDispatch(order=(FIRST_PROVIDER, SECOND_PROVIDER))
    candidates = (
        ProviderAvailability(provider_id=FIRST_PROVIDER, available=ElectricalPower(5)),
        ProviderAvailability(provider_id=SECOND_PROVIDER, available=ElectricalPower(5)),
    )

    assert strategy.allocate(ElectricalPower(12), candidates) == {
        FIRST_PROVIDER: ElectricalPower(5),
        SECOND_PROVIDER: ElectricalPower(7),
    }


def test_zero_demand_allocates_zero_to_every_provider():
    strategy = PriorityDispatch(order=(FIRST_PROVIDER, SECOND_PROVIDER))
    candidates = (
        ProviderAvailability(provider_id=FIRST_PROVIDER, available=None),
        ProviderAvailability(provider_id=SECOND_PROVIDER, available=ElectricalPower(5)),
    )

    assert strategy.allocate(ElectricalPower(0), candidates) == {
        FIRST_PROVIDER: ElectricalPower(0),
        SECOND_PROVIDER: ElectricalPower(0),
    }


@pytest.mark.parametrize(
    ("demand", "candidates"),
    [
        (
            ElectricalPower(7),
            (
                ProviderAvailability(provider_id=FIRST_PROVIDER, available=ElectricalPower(5)),
                ProviderAvailability(provider_id=SECOND_PROVIDER, available=ElectricalPower(5)),
            ),
        ),
        (
            ElectricalPower(12),
            (
                ProviderAvailability(provider_id=FIRST_PROVIDER, available=ElectricalPower(5)),
                ProviderAvailability(provider_id=SECOND_PROVIDER, available=ElectricalPower(5)),
            ),
        ),
        (
            ElectricalPower(12),
            (
                ProviderAvailability(provider_id=FIRST_PROVIDER, available=None),
                ProviderAvailability(provider_id=SECOND_PROVIDER, available=ElectricalPower(5)),
            ),
        ),
    ],
)
def test_allocations_always_sum_to_demand(
    demand: ElectricalPower,
    candidates: tuple[ProviderAvailability, ...],
):
    strategy = PriorityDispatch(order=(FIRST_PROVIDER, SECOND_PROVIDER))

    allocations = strategy.allocate(demand, candidates)

    assert sum(allocation.value for allocation in allocations.values()) == demand.value


def test_rejects_order_referencing_provider_missing_from_candidates():
    strategy = PriorityDispatch(order=(FIRST_PROVIDER, SECOND_PROVIDER))
    candidates = (ProviderAvailability(provider_id=FIRST_PROVIDER, available=ElectricalPower(5)),)

    with pytest.raises(InvalidDispatchError, match="missing from the candidates"):
        strategy.allocate(ElectricalPower(3), candidates)


def test_rejects_empty_order():
    strategy = PriorityDispatch(order=())
    candidates = (ProviderAvailability(provider_id=FIRST_PROVIDER, available=ElectricalPower(5)),)

    with pytest.raises(InvalidDispatchError, match="at least one provider"):
        strategy.allocate(ElectricalPower(3), candidates)


def test_ignores_candidates_that_are_not_in_the_order():
    strategy = PriorityDispatch(order=(FIRST_PROVIDER,))
    candidates = (
        ProviderAvailability(provider_id=FIRST_PROVIDER, available=ElectricalPower(10)),
        ProviderAvailability(provider_id=SECOND_PROVIDER, available=ElectricalPower(10)),
    )

    assert strategy.allocate(ElectricalPower(4), candidates) == {
        FIRST_PROVIDER: ElectricalPower(4),
        SECOND_PROVIDER: ElectricalPower(0),
    }
