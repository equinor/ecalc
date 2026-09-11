from uuid import UUID

import pytest

from libecalc.energy.dispatch import Candidate, PriorityDispatch
from libecalc.energy.energy_types import ElectricalPower
from libecalc.energy.energy_unit import EnergyUnitId
from libecalc.energy.errors import InvalidDispatchError

FIRST_CANDIDATE = EnergyUnitId(UUID(int=1))
SECOND_CANDIDATE = EnergyUnitId(UUID(int=2))
THIRD_CANDIDATE = EnergyUnitId(UUID(int=3))


def test_exact_fit():
    strategy = PriorityDispatch(order=(FIRST_CANDIDATE, SECOND_CANDIDATE))
    candidates = (
        Candidate(candidate_id=FIRST_CANDIDATE, available=ElectricalPower(5)),
        Candidate(candidate_id=SECOND_CANDIDATE, available=ElectricalPower(5)),
    )

    assert strategy.allocate(ElectricalPower(10), candidates) == {
        FIRST_CANDIDATE: ElectricalPower(5),
        SECOND_CANDIDATE: ElectricalPower(5),
    }


def test_spills_to_second_and_third_candidate():
    strategy = PriorityDispatch(order=(FIRST_CANDIDATE, SECOND_CANDIDATE, THIRD_CANDIDATE))
    candidates = (
        Candidate(candidate_id=FIRST_CANDIDATE, available=ElectricalPower(5)),
        Candidate(candidate_id=SECOND_CANDIDATE, available=ElectricalPower(4)),
        Candidate(candidate_id=THIRD_CANDIDATE, available=ElectricalPower(10)),
    )

    assert strategy.allocate(ElectricalPower(12), candidates) == {
        FIRST_CANDIDATE: ElectricalPower(5),
        SECOND_CANDIDATE: ElectricalPower(4),
        THIRD_CANDIDATE: ElectricalPower(3),
    }


def test_reversing_order_changes_allocation():
    candidates = (
        Candidate(candidate_id=FIRST_CANDIDATE, available=ElectricalPower(10)),
        Candidate(candidate_id=SECOND_CANDIDATE, available=ElectricalPower(10)),
    )

    first_priority = PriorityDispatch(order=(FIRST_CANDIDATE, SECOND_CANDIDATE)).allocate(
        ElectricalPower(6), candidates
    )
    second_priority = PriorityDispatch(order=(SECOND_CANDIDATE, FIRST_CANDIDATE)).allocate(
        ElectricalPower(6), candidates
    )

    assert first_priority == {
        FIRST_CANDIDATE: ElectricalPower(6),
        SECOND_CANDIDATE: ElectricalPower(0),
    }
    assert second_priority == {
        FIRST_CANDIDATE: ElectricalPower(0),
        SECOND_CANDIDATE: ElectricalPower(6),
    }


def test_unlimited_first_candidate_starves_remaining_candidates():
    strategy = PriorityDispatch(order=(FIRST_CANDIDATE, SECOND_CANDIDATE, THIRD_CANDIDATE))
    candidates = (
        Candidate(candidate_id=FIRST_CANDIDATE, available=None),
        Candidate(candidate_id=SECOND_CANDIDATE, available=ElectricalPower(5)),
        Candidate(candidate_id=THIRD_CANDIDATE, available=ElectricalPower(5)),
    )

    assert strategy.allocate(ElectricalPower(12), candidates) == {
        FIRST_CANDIDATE: ElectricalPower(12),
        SECOND_CANDIDATE: ElectricalPower(0),
        THIRD_CANDIDATE: ElectricalPower(0),
    }


def test_insufficient_capacity_overflows_on_last_candidate():
    strategy = PriorityDispatch(order=(FIRST_CANDIDATE, SECOND_CANDIDATE))
    candidates = (
        Candidate(candidate_id=FIRST_CANDIDATE, available=ElectricalPower(5)),
        Candidate(candidate_id=SECOND_CANDIDATE, available=ElectricalPower(5)),
    )

    assert strategy.allocate(ElectricalPower(12), candidates) == {
        FIRST_CANDIDATE: ElectricalPower(5),
        SECOND_CANDIDATE: ElectricalPower(7),
    }


def test_zero_demand_allocates_zero_to_every_candidate():
    strategy = PriorityDispatch(order=(FIRST_CANDIDATE, SECOND_CANDIDATE))
    candidates = (
        Candidate(candidate_id=FIRST_CANDIDATE, available=None),
        Candidate(candidate_id=SECOND_CANDIDATE, available=ElectricalPower(5)),
    )

    assert strategy.allocate(ElectricalPower(0), candidates) == {
        FIRST_CANDIDATE: ElectricalPower(0),
        SECOND_CANDIDATE: ElectricalPower(0),
    }


def test_rejects_order_referencing_candidate_missing_from_allocation_input():
    strategy = PriorityDispatch(order=(FIRST_CANDIDATE, SECOND_CANDIDATE))
    candidates = (Candidate(candidate_id=FIRST_CANDIDATE, available=ElectricalPower(5)),)

    with pytest.raises(InvalidDispatchError, match="missing from the allocation input"):
        strategy.allocate(ElectricalPower(3), candidates)


def test_rejects_empty_order():
    strategy = PriorityDispatch(order=())
    candidates = (Candidate(candidate_id=FIRST_CANDIDATE, available=ElectricalPower(5)),)

    with pytest.raises(InvalidDispatchError, match="at least one candidate"):
        strategy.allocate(ElectricalPower(3), candidates)


def test_ignores_candidates_that_are_not_in_the_order():
    strategy = PriorityDispatch(order=(FIRST_CANDIDATE,))
    candidates = (
        Candidate(candidate_id=FIRST_CANDIDATE, available=ElectricalPower(10)),
        Candidate(candidate_id=SECOND_CANDIDATE, available=ElectricalPower(10)),
    )

    assert strategy.allocate(ElectricalPower(4), candidates) == {
        FIRST_CANDIDATE: ElectricalPower(4),
        SECOND_CANDIDATE: ElectricalPower(0),
    }
