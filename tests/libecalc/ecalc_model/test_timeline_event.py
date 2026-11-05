from datetime import datetime

import pytest

from libecalc.ecalc_model.timeline_event import (
    TimelineEvent,
    TimelineEventNotFoundException,
    TimelineEventService,
    TimelineEventType,
)


def _event(reference: str, from_when: datetime) -> TimelineEvent:
    return TimelineEvent(
        reference=reference, title=reference, type=TimelineEventType.TIE_IN, from_when=from_when, description=None
    )


def test_get_event_by_reference():
    event = _event("tie_in", datetime(2025, 1, 1))
    service = TimelineEventService(timeline_events=[event, _event("rebundle", datetime(2028, 6, 1))])

    assert service.get_event_by_reference("tie_in") == event


def test_get_event_by_unknown_reference_raises():
    service = TimelineEventService(timeline_events=[_event("tie_in", datetime(2025, 1, 1))])

    with pytest.raises(TimelineEventNotFoundException):
        service.get_event_by_reference("unknown")


def test_get_event_dates():
    service = TimelineEventService(
        timeline_events=[_event("tie_in", datetime(2025, 1, 1)), _event("rebundle", datetime(2028, 6, 1))]
    )

    assert service.get_event_dates() == {datetime(2025, 1, 1), datetime(2028, 6, 1)}
    assert TimelineEventService(timeline_events=[]).get_event_dates() == set()
