from datetime import datetime
from enum import StrEnum

from libecalc.common.ddd import value_object


# TODO: Unknown types or categories. Does it even make sense to specify in hierarchy?
# We will figure out more soon
class EcalcEventType(StrEnum):
    OPERATIONAL_MEASURE = "OPERATIONAL_MEASURE"
    ENERGY_EFFICIENCY_MEASURE = "ENERGY_EFFICIENCY_MEASURE"
    CALIBRATION = "CALIBRATION"
    TIE_IN = "TIE_IN"
    OTHER = "OTHER"


class ProcessEventType(StrEnum):
    INCREASED_GAS_RATE = "INCREASED_GAS_RATE"
    INCREASED_WATER_INJECTION = "INCREASED_WATER_INJECTION"
    OTHER = "OTHER"


class EnergyEventType(StrEnum):
    FUEL_SWITCH = "FUEL_SWITCH"
    OTHER = "OTHER"


@value_object
class ProcessEvent:
    name: str
    type: ProcessEventType
    description: str | None


@value_object
class EnergyEvent:
    name: str
    type: EnergyEventType
    description: str | None


@value_object
class EcalcEvent:
    name: str
    type: EcalcEventType
    start: datetime
    description: str | None
    process_events: list[ProcessEvent]
    energy_events: list[EnergyEvent]


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

    def get_time_steps(self) -> set[datetime]:
        return {ecalc_event.start for ecalc_event in self._ecalc_events}

    def get_event_by_energy_name(self, name: str) -> EcalcEvent | None:
        for ecalc_event in self._ecalc_events:
            for energy_event in ecalc_event.energy_events:
                if energy_event.name == name:
                    return ecalc_event
        return None
