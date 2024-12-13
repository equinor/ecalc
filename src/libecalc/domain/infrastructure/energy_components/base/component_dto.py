from abc import ABC, abstractmethod
from typing import Optional

from pydantic import ConfigDict, Field, field_validator
from pydantic_core.core_schema import ValidationInfo

from libecalc.common.component_type import ComponentType
from libecalc.common.consumption_type import ConsumptionType
from libecalc.common.string.string_utils import generate_id
from libecalc.common.time_utils import Period
from libecalc.common.units import Unit
from libecalc.common.utils.rates import RateType
from libecalc.domain.infrastructure.energy_components.utils import _convert_keys_in_dictionary_from_str_to_periods
from libecalc.dto.base import EcalcBaseModel
from libecalc.dto.fuel_type import FuelType
from libecalc.dto.types import ConsumerUserDefinedCategoryType
from libecalc.dto.utils.validators import (
    ComponentNameStr,
    ExpressionType,
    validate_temporal_model,
)
from libecalc.expression import Expression


class Component(EcalcBaseModel, ABC):
    component_type: ComponentType

    @property
    @abstractmethod
    def id(self) -> str: ...


class BaseComponent(Component, ABC):
    name: ComponentNameStr

    regularity: dict[Period, Expression]

    _validate_base_temporal_model = field_validator("regularity")(validate_temporal_model)

    @field_validator("regularity", mode="before")
    @classmethod
    def check_regularity(cls, regularity):
        if isinstance(regularity, dict) and len(regularity.values()) > 0:
            regularity = _convert_keys_in_dictionary_from_str_to_periods(regularity)
        return regularity


class BaseEquipment(BaseComponent, ABC):
    user_defined_category: dict[Period, ConsumerUserDefinedCategoryType] = Field(..., validate_default=True)

    @property
    def id(self) -> str:
        return generate_id(self.name)

    @field_validator("user_defined_category", mode="before")
    def check_user_defined_category(cls, user_defined_category, info: ValidationInfo):
        """Provide which value and context to make it easier for user to correct wrt mandatory changes."""
        if isinstance(user_defined_category, dict) and len(user_defined_category.values()) > 0:
            user_defined_category = _convert_keys_in_dictionary_from_str_to_periods(user_defined_category)
            for user_category in user_defined_category.values():
                if user_category not in list(ConsumerUserDefinedCategoryType):
                    name_context_str = ""
                    if (name := info.data.get("name")) is not None:
                        name_context_str = f"with the name {name}"

                    raise ValueError(
                        f"CATEGORY: {user_category} is not allowed for {cls.__name__} {name_context_str}. Valid categories are: {[(consumer_user_defined_category.value) for consumer_user_defined_category in ConsumerUserDefinedCategoryType]}"
                    )

        return user_defined_category


class BaseConsumer(BaseEquipment, ABC):
    """Base class for all consumers."""

    consumes: ConsumptionType
    fuel: Optional[dict[Period, FuelType]] = None

    @field_validator("fuel", mode="before")
    @classmethod
    def validate_fuel_exist(cls, fuel, info: ValidationInfo):
        """
        Make sure fuel is set if consumption type is FUEL.
        """
        if isinstance(fuel, dict) and len(fuel.values()) > 0:
            fuel = _convert_keys_in_dictionary_from_str_to_periods(fuel)
        if info.data.get("consumes") == ConsumptionType.FUEL and (fuel is None or len(fuel) < 1):
            msg = f"Missing fuel for fuel consumer '{info.data.get('name')}'"
            raise ValueError(msg)
        return fuel


class ExpressionTimeSeries(EcalcBaseModel):
    value: ExpressionType
    unit: Unit
    type: Optional[RateType] = None


class ExpressionStreamConditions(EcalcBaseModel):
    rate: Optional[ExpressionTimeSeries] = None
    pressure: Optional[ExpressionTimeSeries] = None
    temperature: Optional[ExpressionTimeSeries] = None
    fluid_density: Optional[ExpressionTimeSeries] = None


ConsumerID = str
PriorityID = str
StreamID = str

SystemStreamConditions = dict[ConsumerID, dict[StreamID, ExpressionStreamConditions]]


class Crossover(EcalcBaseModel):
    model_config = ConfigDict(populate_by_name=True)

    stream_name: Optional[str] = Field(None)
    from_component_id: str
    to_component_id: str


class SystemComponentConditions(EcalcBaseModel):
    crossover: list[Crossover]
