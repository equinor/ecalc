from enum import Enum


class ProcessUnitType(str, Enum):
    COMPRESSOR = "Compressor"
    LIQUID_REMOVER = "Liquid remover"
    MIXER = "Mixer"

    PRESSURE_MODIFIER = "Pressure modifier"
    RATE_MODIFIER = "Rate modifier"
    SPLITTER = "Splitter"
    TEMPERATURE_SETTER = "Temperature setter"
