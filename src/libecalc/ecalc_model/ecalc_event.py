from datetime import datetime
from enum import StrEnum

from libecalc.common.ddd import value_object


class EcalcEventType(StrEnum):
    PROCESS = "PROCESS"
    ENERGY = "ENERGY"
    ALL = "ALL"


class ProcessEventType(StrEnum):
    REBUNDLE = "REBUNDLE"
    REVAMP = "REVAMP"


@value_object
class EcalcEvent:
    name: str
    type: EcalcEventType
    start: datetime
    description: str | None


@value_object
class ProcessEvent:
    name: str
    type: ProcessEventType
    description: str | None
    ecalc_event_ref: str  # name of the referenced EcalcEvent
