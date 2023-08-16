from enum import Enum


class CompressorPressureState(str, Enum):
    INLET_PRESSURE = "INLET_PRESSURE"
    OUTLET_PRESSURE = "OUTLET_PRESSURE"
