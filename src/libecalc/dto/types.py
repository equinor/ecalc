from enum import Enum
from typing import List, Optional

from libecalc.dto.base import EcalcBaseModel, FuelTypeUserDefinedCategoryType
from libecalc.dto.emission import Emission
from libecalc.dto.utils.validators import convert_expression
from libecalc.expression import Expression
from pydantic import Field, validator


class ConsumptionType(str, Enum):
    FUEL = "FUEL"
    ELECTRICITY = "ELECTRICITY"


class EnergyUsageType(str, Enum):
    FUEL = "FUEL"
    POWER = "POWER"


class RateType(str, Enum):
    STREAM_DAY = "STREAM_DAY"
    CALENDAR_DAY = "CALENDAR_DAY"


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
    """An installation/model/component may change fuel over time, due to setup changes,
    production, and the cost may also change on different predictive models.
    """

    name: str
    user_defined_category: Optional[FuelTypeUserDefinedCategoryType] = None
    price: Optional[Expression]
    emissions: List[Emission] = Field(default_factory=list)

    _convert_expression = validator("price", allow_reuse=True, pre=True)(convert_expression)

    @validator("price", pre=True)
    def convert_price(cls, price):
        # NOTE: This is called after validator/converter above, hence wraps value in an Expression
        # This is needed when price is explicitly set to None, e.g. when parsed in YAML
        return price if price is not None else Expression.setup_from_expression(value=0.0)

    @validator("user_defined_category", pre=True, always=True)
    def check_user_defined_category(cls, user_defined_category, values):
        """Provide which value and context to make it easier for user to correct wrt mandatory changes."""
        if user_defined_category is not None:
            if user_defined_category not in list(FuelTypeUserDefinedCategoryType):
                name = ""
                if values.get("name") is not None:
                    name = f"with the name {values.get('name')}"

                raise ValueError(
                    f"CATEGORY: {user_defined_category} is not allowed for {cls.__name__} {name}. Valid categories are: {[str(fuel_type_user_defined_category.value) for fuel_type_user_defined_category in FuelTypeUserDefinedCategoryType]}"
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
