from datetime import datetime
from enum import StrEnum

from libecalc.common.ddd import value_object


class TimelineEventType(StrEnum):
    OPERATIONAL_MEASURE = "OPERATIONAL_MEASURE"
    ENERGY_EFFICIENCY_MEASURE = "ENERGY_EFFICIENCY_MEASURE"
    CALIBRATION = "CALIBRATION"
    TIE_IN = "TIE_IN"
    INCREASED_GAS_RATE = "INCREASED_GAS_RATE"
    INCREASED_WATER_INJECTION = "INCREASED_WATER_INJECTION"
    FUEL_SWITCH = "FUEL_SWITCH"
    OTHER = "OTHER"


@value_object
class TimelineEvent:
    name: str
    type: TimelineEventType
    from_: datetime
    description: str | None


class TimelineEventService:
    def __init__(self, timeline_events: list[TimelineEvent]):
        self._timeline_events = timeline_events or []

    def get_event_by_name(self, name: str) -> TimelineEvent | None:
        for timeline_event in self._timeline_events:
            if timeline_event.name == name:
                return timeline_event
        return None

    def get_time_steps(self) -> set[datetime]:
        return {timeline_event.from_ for timeline_event in self._timeline_events}
