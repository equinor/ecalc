from enum import Enum


class CompressorInputPressures(str, Enum):
    inlet_pressure = "inlet_pressure"
    outlet_pressure = "outlet_pressure"
