from enum import Enum


class ConsumerFunctionType(str, Enum):
    SINGLE = "SINGLE"
    SYSTEM = "SYSTEM"
