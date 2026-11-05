from datetime import datetime
from enum import StrEnum

from libecalc.common.ddd import value_object
from libecalc.common.errors.ecalc_validation_error import EcalcValidationException


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
    reference: str
    title: str
    type: TimelineEventType
    from_date: datetime
    description: str | None


class TimelineEventNotFoundException(EcalcValidationException):
    def __init__(self, reference: str):
        super().__init__(f"Timeline event '{reference}' does not exist in TIMELINE.EVENTS.")


class TimelineEventService:
    def __init__(self, timeline_events: list[TimelineEvent]):
        self._timeline_events = {timeline_event.reference: timeline_event for timeline_event in timeline_events}

    def has_event(self, reference: str) -> bool:
        return reference in self._timeline_events

    def get_event_by_reference(self, reference: str) -> TimelineEvent:
        if reference not in self._timeline_events:
            raise TimelineEventNotFoundException(reference)
        return self._timeline_events[reference]

    def get_event_dates(self) -> set[datetime]:
        return {timeline_event.from_date for timeline_event in self._timeline_events.values()}
