from datetime import datetime
from uuid import UUID

import pytest

from libecalc.common.time_utils import Period
from libecalc.energy.energy_unit import EnergyUnitId
from libecalc.energy.errors import InvalidEnergyNetworkInputError
from libecalc.energy.input_schedule import InputSchedule

FIRST_CANDIDATE = EnergyUnitId(UUID(int=1))
SECOND_CANDIDATE = EnergyUnitId(UUID(int=2))
THIRD_CANDIDATE = EnergyUnitId(UUID(int=3))


def test_active_at_uses_initial_before_any_change():
    schedule = InputSchedule(
        initial=FIRST_CANDIDATE,
        changes=((datetime(2020, 1, 1), SECOND_CANDIDATE),),
    )

    assert schedule.active_at(Period(start=datetime(2019, 1, 1), end=datetime(2019, 12, 31))) == FIRST_CANDIDATE


def test_active_at_switches_on_change_time():
    schedule = InputSchedule(
        initial=FIRST_CANDIDATE,
        changes=(
            (datetime(2020, 1, 1), SECOND_CANDIDATE),
            (datetime(2021, 1, 1), THIRD_CANDIDATE),
        ),
    )

    assert schedule.active_at(Period(start=datetime(2019, 6, 1), end=datetime(2020, 1, 1))) == FIRST_CANDIDATE
    assert schedule.active_at(Period(start=datetime(2020, 6, 1), end=datetime(2021, 1, 1))) == SECOND_CANDIDATE
    assert schedule.active_at(Period(start=datetime(2021, 6, 1), end=datetime(2022, 1, 1))) == THIRD_CANDIDATE


def test_active_at_period_starting_exactly_on_a_change_time_uses_the_new_candidate():
    schedule = InputSchedule(
        initial=FIRST_CANDIDATE,
        changes=((datetime(2020, 1, 1), SECOND_CANDIDATE),),
    )

    assert schedule.active_at(Period(start=datetime(2020, 1, 1), end=datetime(2020, 2, 1))) == SECOND_CANDIDATE


def test_get_candidate_ids_includes_initial_and_every_change():
    schedule = InputSchedule(
        initial=FIRST_CANDIDATE,
        changes=(
            (datetime(2020, 1, 1), SECOND_CANDIDATE),
            (datetime(2021, 1, 1), THIRD_CANDIDATE),
        ),
    )

    assert schedule.get_candidate_ids() == frozenset((FIRST_CANDIDATE, SECOND_CANDIDATE, THIRD_CANDIDATE))


def test_rejects_changes_not_strictly_increasing_in_time():
    with pytest.raises(InvalidEnergyNetworkInputError, match="strictly increasing"):
        InputSchedule(
            initial=FIRST_CANDIDATE,
            changes=(
                (datetime(2021, 1, 1), SECOND_CANDIDATE),
                (datetime(2020, 1, 1), THIRD_CANDIDATE),
            ),
        )


def test_rejects_changes_with_the_same_time():
    with pytest.raises(InvalidEnergyNetworkInputError, match="strictly increasing"):
        InputSchedule(
            initial=FIRST_CANDIDATE,
            changes=(
                (datetime(2020, 1, 1), SECOND_CANDIDATE),
                (datetime(2020, 1, 1), THIRD_CANDIDATE),
            ),
        )


def test_rejects_a_repeated_switch_to_the_already_active_candidate():
    with pytest.raises(InvalidEnergyNetworkInputError, match="no-op switch"):
        InputSchedule(
            initial=FIRST_CANDIDATE,
            changes=((datetime(2020, 1, 1), FIRST_CANDIDATE),),
        )


def test_rejects_a_repeated_switch_to_the_same_candidate_as_the_previous_change():
    with pytest.raises(InvalidEnergyNetworkInputError, match="no-op switch"):
        InputSchedule(
            initial=FIRST_CANDIDATE,
            changes=(
                (datetime(2020, 1, 1), SECOND_CANDIDATE),
                (datetime(2021, 1, 1), SECOND_CANDIDATE),
            ),
        )
