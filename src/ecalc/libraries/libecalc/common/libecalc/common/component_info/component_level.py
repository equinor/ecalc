from enum import Enum


class ComponentLevel(str, Enum):
    ASSET = "ASSET"
    INSTALLATION = "INSTALLATION"
    GENERATOR_SET = "GENERATOR_SET"
    SYSTEM = "SYSTEM"
    CONSUMER = "CONSUMER"
    MODEL = "MODEL"
