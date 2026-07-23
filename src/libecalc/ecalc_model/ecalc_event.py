from datetime import datetime
from enum import StrEnum

from libecalc.common.ddd import value_object


# TODO: Unknown types or categories. Does it even make sense to specify in hierarchy?
# We will figure out more soon
class EcalcEventType(StrEnum):
    OPERATIONAL_MEASUREMENT = "OPERATIONAL_MEASUREMENT"
    ENERGY_EFFICIENCY_MEASUREMENT = "ENERGY_EFFICIENCY_MEASUREMENT"
    CALIBRATION = "CALIBRATION"
    TIE_IN = "TIE_IN"
    OTHER = "OTHER"


class ProcessEventType(StrEnum):
    INCREASED_GAS_RATE = "INCREASED_GAS_RATE"
    INCREASED_WATER_INJECTION = "INCREASED_WATER_INJECTION"
    OTHER = "OTHER"


@value_object
class ProcessEvent:
    name: str
    type: ProcessEventType
    description: str | None


@value_object
class EcalcEvent:
    name: str
    type: EcalcEventType
    start: datetime
    description: str | None
    process_events: list[ProcessEvent]


class EcalcEventService:
    def __init__(self, ecalc_events: list[EcalcEvent]):
        self._ecalc_events = ecalc_events or []

    def get_event_by_name(self, name: str) -> EcalcEvent | None:
        for ecalc_event in self._ecalc_events:
            if ecalc_event.name == name:
                return ecalc_event
        return None

    def get_event_by_process_name(self, name: str) -> EcalcEvent | None:
        for ecalc_event in self._ecalc_events:
            for process_event in ecalc_event.process_events:
                if process_event.name == name:
                    return ecalc_event
        return None
