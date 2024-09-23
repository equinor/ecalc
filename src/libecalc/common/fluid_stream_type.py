from enum import Enum


class FluidStreamType(str, Enum):
    INGOING = "INGOING"
    OUTGOING = "OUTGOING"
