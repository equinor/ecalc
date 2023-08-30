from enum import Enum


class CompressorPressureType(str, Enum):
    INLET_PRESSURE = "INLET_PRESSURE"
    OUTLET_PRESSURE = "OUTLET_PRESSURE"
