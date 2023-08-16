from enum import Enum


class CompressorPressureState(str, Enum):
    inlet_pressure = "inlet_pressure"
    outlet_pressure = "outlet_pressure"
