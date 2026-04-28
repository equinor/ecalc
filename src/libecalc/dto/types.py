from enum import StrEnum


class ChartRateUnit(StrEnum):
    AM3_PER_HOUR = "AM3_PER_HOUR"


class ChartPolytropicHeadUnit(StrEnum):
    J_PER_KG = "JOULE_PER_KG"
    KJ_PER_KG = "KJ_PER_KG"
    M = "M"


class ChartEfficiencyUnit(StrEnum):
    FRACTION = "FRACTION"
    PERCENTAGE = "PERCENTAGE"


class ChartControlMarginUnit(StrEnum):
    FRACTION = "FRACTION"
    PERCENTAGE = "PERCENTAGE"


class InterpolationType(StrEnum):
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    LINEAR = "LINEAR"
