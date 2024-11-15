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


class ConsumerUserDefinedCategoryType(str, Enum):
    """
    Consumer category
    """

    BASE_LOAD = "BASE-LOAD"
    COLD_VENTING_FUGITIVE = "COLD-VENTING-FUGITIVE"
    COMPRESSOR = "COMPRESSOR"
    FIXED_PRODUCTION_LOAD = "FIXED-PRODUCTION-LOAD"
    FLARE = "FLARE"
    MISCELLANEOUS = "MISCELLANEOUS"
    PUMP = "PUMP"
    GAS_DRIVEN_COMPRESSOR = "GAS-DRIVEN-COMPRESSOR"
    TURBINE_GENERATOR = "TURBINE-GENERATOR"
    POWER_FROM_SHORE = "POWER-FROM-SHORE"
    OFFSHORE_WIND = "OFFSHORE-WIND"
    LOADING = "LOADING"
    STORAGE = "STORAGE"
    STEAM_TURBINE_GENERATOR = "STEAM-TURBINE-GENERATOR"
    BOILER = "BOILER"
    HEATER = "HEATER"


class InstallationUserDefinedCategoryType(str, Enum):
    """
    Installation category
    """

    FIXED = "FIXED"
    MOBILE = "MOBILE"


class FuelTypeUserDefinedCategoryType(str, Enum):
    FUEL_GAS = "FUEL-GAS"
    DIESEL = "DIESEL"
