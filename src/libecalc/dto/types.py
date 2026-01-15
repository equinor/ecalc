from enum import Enum


class ChartRateUnit(str, Enum):
    AM3_PER_HOUR = "AM3_PER_HOUR"


class ChartPolytropicHeadUnit(str, Enum):
    J_PER_KG = "JOULE_PER_KG"
    KJ_PER_KG = "KJ_PER_KG"
    M = "M"


class ChartEfficiencyUnit(str, Enum):
    FRACTION = "FRACTION"
    PERCENTAGE = "PERCENTAGE"


class ChartControlMarginUnit(str, Enum):
    FRACTION = "FRACTION"
    PERCENTAGE = "PERCENTAGE"


class InterpolationType(str, Enum):
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    LINEAR = "LINEAR"
