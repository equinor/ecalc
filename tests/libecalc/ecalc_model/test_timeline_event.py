from datetime import datetime

from libecalc.ecalc_model.timeline_event import TimelineEvent, TimelineEventService, TimelineEventType


def _event(name: str, from_: datetime) -> TimelineEvent:
    return TimelineEvent(name=name, type=TimelineEventType.TIE_IN, from_=from_, description=None)


def test_get_event_by_name():
    event = _event("tie_in", datetime(2025, 1, 1))
    service = TimelineEventService(timeline_events=[event, _event("rebundle", datetime(2028, 6, 1))])

    assert service.get_event_by_name("tie_in") == event
    assert service.get_event_by_name("unknown") is None


def test_get_time_steps():
    service = TimelineEventService(
        timeline_events=[_event("tie_in", datetime(2025, 1, 1)), _event("rebundle", datetime(2028, 6, 1))]
    )

    assert service.get_time_steps() == {datetime(2025, 1, 1), datetime(2028, 6, 1)}
    assert TimelineEventService(timeline_events=[]).get_time_steps() == set()
