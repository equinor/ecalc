from enum import StrEnum


class ComponentLevel(StrEnum):
    ASSET = "ASSET"
    INSTALLATION = "INSTALLATION"
    GENERATOR_SET = "GENERATOR_SET"
    SYSTEM = "SYSTEM"
    CONSUMER = "CONSUMER"
    MODEL = "MODEL"
