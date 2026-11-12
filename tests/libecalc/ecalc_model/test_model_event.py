from datetime import datetime
from uuid import UUID

import pytest

from libecalc.ecalc_model.model_event import (
    DuplicateModelEventTimeException,
    EnergyUnitEventChangeType,
    EnergyUnitModelEvent,
    active_model,
    validate_unique_change_times,
)
from libecalc.energy.ids import EnergyUnitId


def model_event(*, change_time: datetime, change_to: str) -> EnergyUnitModelEvent[str]:
    return EnergyUnitModelEvent(
        change_target=EnergyUnitId(UUID(int=1)),
        change_type=EnergyUnitEventChangeType.REBUNDLE,
        change_time=change_time,
        change_to=change_to,
    )


class TestActiveModel:
    def test_without_events_the_initial_model_is_active(self):
        assert active_model(initial_model="initial", model_events=[], at=datetime(2030, 1, 1)) == "initial"

    def test_initial_model_is_active_before_the_first_event(self):
        events = [model_event(change_time=datetime(2025, 1, 1), change_to="upgraded")]

        assert active_model(initial_model="initial", model_events=events, at=datetime(2024, 12, 31)) == "initial"

    def test_event_is_active_from_its_change_time(self):
        events = [model_event(change_time=datetime(2025, 1, 1), change_to="upgraded")]

        assert active_model(initial_model="initial", model_events=events, at=datetime(2025, 1, 1)) == "upgraded"

    def test_latest_started_event_is_active(self):
        events = [
            model_event(change_time=datetime(2025, 1, 1), change_to="first"),
            model_event(change_time=datetime(2027, 1, 1), change_to="second"),
            model_event(change_time=datetime(2029, 1, 1), change_to="third"),
        ]

        assert active_model(initial_model="initial", model_events=events, at=datetime(2024, 1, 1)) == "initial"
        assert active_model(initial_model="initial", model_events=events, at=datetime(2026, 1, 1)) == "first"
        assert active_model(initial_model="initial", model_events=events, at=datetime(2028, 1, 1)) == "second"
        assert active_model(initial_model="initial", model_events=events, at=datetime(2040, 1, 1)) == "third"

    def test_event_order_does_not_matter(self):
        events = [
            model_event(change_time=datetime(2027, 1, 1), change_to="second"),
            model_event(change_time=datetime(2025, 1, 1), change_to="first"),
        ]

        assert active_model(initial_model="initial", model_events=events, at=datetime(2026, 1, 1)) == "first"
        assert active_model(initial_model="initial", model_events=events, at=datetime(2027, 1, 1)) == "second"


class TestValidateUniqueChangeTimes:
    def test_events_on_different_dates_are_accepted(self):
        validate_unique_change_times(
            [
                model_event(change_time=datetime(2025, 1, 1), change_to="first"),
                model_event(change_time=datetime(2027, 1, 1), change_to="second"),
            ]
        )

    def test_events_on_the_same_date_are_rejected(self):
        with pytest.raises(DuplicateModelEventTimeException, match="2025-01-01"):
            validate_unique_change_times(
                [
                    model_event(change_time=datetime(2025, 1, 1), change_to="first"),
                    model_event(change_time=datetime(2025, 1, 1), change_to="second"),
                ]
            )
