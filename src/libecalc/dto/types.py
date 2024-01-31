from enum import Enum
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_core.core_schema import ValidationInfo

from libecalc.dto.base import EcalcBaseModel, FuelTypeUserDefinedCategoryType
from libecalc.dto.emission import Emission


class ConsumptionType(str, Enum):
    FUEL = "FUEL"
    ELECTRICITY = "ELECTRICITY"


class EnergyUsageType(str, Enum):
    FUEL = "FUEL"
    POWER = "POWER"


class ConsumerType(str, Enum):
    DIRECT = "DIRECT"
    COMPRESSOR = "COMPRESSOR"
    PUMP = "PUMP"
    COMPRESSOR_SYSTEM = "COMPRESSOR_SYSTEM"
    PUMP_SYSTEM = "PUMP_SYSTEM"
    TABULATED = "TABULATED"
    GENERATOR_SET_SIMPLE = "GENERATOR_SET_SIMPLE"


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


class ChartType(str, Enum):
    SINGLE_SPEED = "SINGLE_SPEED_CHART"
    VARIABLE_SPEED = "VARIABLE_SPEED_CHART"
    GENERIC_FROM_DESIGN_POINT = "GENERIC_CHART_FROM_DESIGN_POINT"
    GENERIC_FROM_INPUT = "GENERIC_CHART_FROM_INPUT"


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


class EoSModel(str, Enum):
    SRK = "SRK"
    PR = "PR"
    GERG_SRK = "GERG_SRK"
    GERG_PR = "GERG_PR"


class FluidStreamFlowRateType(str, Enum):
    STANDARD_RATE = "Sm3/day"  # Standard conditions are 15 C at 1 atm = 1.01325 bara
    ACTUAL_VOLUME_RATE = "Am3/hr"
    MASS_RATE = "kg/hr"


class FixedSpeedPressureControl(str, Enum):
    UPSTREAM_CHOKE = "UPSTREAM_CHOKE"
    DOWNSTREAM_CHOKE = "DOWNSTREAM_CHOKE"
    INDIVIDUAL_ASV_PRESSURE = "INDIVIDUAL_ASV_PRESSURE"
    INDIVIDUAL_ASV_RATE = "INDIVIDUAL_ASV_RATE"
    COMMON_ASV = "COMMON_ASV"


class FluidStreamType(str, Enum):
    INGOING = "INGOING"
    OUTGOING = "OUTGOING"


# TODO: time series types defined both here and in yaml_entities.py. Should be defined once.
class TimeSeriesType(str, Enum):
    MISCELLANEOUS = "MISCELLANEOUS"
    DEFAULT = "DEFAULT"


class InterpolationType(str, Enum):
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    LINEAR = "LINEAR"


class FuelType(EcalcBaseModel):
    name: str
    user_defined_category: Optional[FuelTypeUserDefinedCategoryType] = Field(default=None, validate_default=True)
    emissions: List[Emission] = Field(default_factory=list)

    @field_validator("user_defined_category", mode="before")
    @classmethod
    def check_user_defined_category(cls, user_defined_category, info: ValidationInfo):
        """Provide which value and context to make it easier for user to correct wrt mandatory changes."""
        if user_defined_category is not None:
            if user_defined_category not in list(FuelTypeUserDefinedCategoryType):
                name_context_str = ""
                if (name := info.data.get("name")) is not None:
                    name_context_str = f"with the name {name}"

                raise ValueError(
                    f"CATEGORY: {user_defined_category} is not allowed for {cls.__name__} {name_context_str}. Valid categories are: {[str(fuel_type_user_defined_category.value) for fuel_type_user_defined_category in FuelTypeUserDefinedCategoryType]}"
                )

        return user_defined_category


class ChartAreaFlag(str, Enum):
    INTERNAL_POINT = "INTERNAL_POINT"
    BELOW_MINIMUM_FLOW_RATE = "BELOW_MINIMUM_FLOW_RATE"
    BELOW_MINIMUM_HEAD = "BELOW_MINIMUM_HEAD"
    BELOW_MINIMUM_SPEED = "BELOW_MINIMUM_SPEED"
    ABOVE_MAXIMUM_FLOW_RATE = "ABOVE_MAXIMUM_FLOW_RATE"
    ABOVE_MAXIMUM_HEAD = "ABOVE_MAXIMUM_HEAD"
    ABOVE_MAXIMUM_SPEED = "ABOVE_MAXIMUM_SPEED"
    BELOW_MINIMUM_SPEED_AND_BELOW_MINIMUM_FLOW_RATE = "BELOW_MINIMUM_SPEED_AND_BELOW_MINIMUM_FLOW_RATE"
    BELOW_MINIMUM_SPEED_AND_ABOVE_MAXIMUM_FLOW_RATE = "BELOW_MINIMUM_SPEED_AND_ABOVE_MAXIMUM_FLOW_RATE"
    NOT_CALCULATED = "NOT_CALCULATED"
    NO_FLOW_RATE = "NO_FLOW_RATE"
