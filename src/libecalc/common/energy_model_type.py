from enum import Enum


class EnergyModelType(str, Enum):
    GENERATOR_SET_SAMPLED = "GENERATOR_SET_SAMPLED"
    TABULATED = "TABULATED"
    COMPRESSOR_SAMPLED = "COMPRESSOR_SAMPLED"
    PUMP_MODEL = "PUMP_MODEL"
    COMPRESSOR_TRAIN_SIMPLIFIED_WITH_KNOWN_STAGES = "COMPRESSOR_TRAIN_SIMPLIFIED_WITH_KNOWN_NUMBER_OF_COMPRESSORS"
    COMPRESSOR_TRAIN_SIMPLIFIED_WITH_UNKNOWN_STAGES = "COMPRESSOR_TRAIN_SIMPLIFIED_WITH_UNKNOWN_NUMBER_OF_COMPRESSORS"
    VARIABLE_SPEED_COMPRESSOR_TRAIN_COMMON_SHAFT = "VARIABLE_SPEED_COMPRESSOR_TRAIN_COMMON_SHAFT"
    SINGLE_SPEED_COMPRESSOR_TRAIN_COMMON_SHAFT = "SINGLE_SPEED_COMPRESSOR_TRAIN_COMMON_SHAFT"
    VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES = (
        "VARIABLE_SPEED_COMPRESSOR_TRAIN_MULTIPLE_STREAMS_AND_PRESSURES"
    )
    TURBINE = "TURBINE"
    COMPRESSOR_WITH_TURBINE = "COMPRESSOR_WITH_TURBINE"