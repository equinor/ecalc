from enum import StrEnum


class EnergyUse(StrEnum):
    BASE_LOAD = "BASE_LOAD"
    COMPRESSION = "COMPRESSION"
    FLARING = "FLARING"
    HEATING = "HEATING"
    PUMPING = "PUMPING"
