from enum import Enum


class FixedSpeedPressureControl(str, Enum):
    UPSTREAM_CHOKE = "UPSTREAM_CHOKE"
    DOWNSTREAM_CHOKE = "DOWNSTREAM_CHOKE"
    INDIVIDUAL_ASV_PRESSURE = "INDIVIDUAL_ASV_PRESSURE"
    INDIVIDUAL_ASV_RATE = "INDIVIDUAL_ASV_RATE"
    COMMON_ASV = "COMMON_ASV"


class InterstagePressureControl:
    def __init__(
        self,
        upstream_pressure_control: FixedSpeedPressureControl,
        downstream_pressure_control: FixedSpeedPressureControl,
    ):
        self.upstream_pressure_control = upstream_pressure_control
        self.downstream_pressure_control = downstream_pressure_control
