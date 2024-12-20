from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Optional, Union

from libecalc.application.energy.emitter import Emitter
from libecalc.application.energy.energy_component import EnergyComponent
from libecalc.common.component_type import ComponentType
from libecalc.common.consumption_type import ConsumptionType
from libecalc.common.string.string_utils import generate_id
from libecalc.common.time_utils import Period
from libecalc.common.units import Unit
from libecalc.common.utils.rates import RateType
from libecalc.domain.infrastructure.energy_components.component_validation_error import (
    ComponentValidationException,
    ModelValidationError,
)
from libecalc.domain.infrastructure.energy_components.utils import _convert_keys_in_dictionary_from_str_to_periods
from libecalc.dto.fuel_type import FuelType
from libecalc.dto.types import ConsumerUserDefinedCategoryType
from libecalc.dto.utils.validators import (
    ExpressionType,
    validate_temporal_model,
)
from libecalc.expression import Expression


class Component(ABC):
    component_type: ComponentType

    @property
    @abstractmethod
    def id(self) -> str: ...


class BaseComponent(Component, ABC):
    def __init__(self, name: str, regularity: dict[Period, Expression]):
        self.name = name
        self.regularity = self.check_regularity(regularity)
        validate_temporal_model(self.regularity)

    @classmethod
    def check_regularity(cls, regularity):
        if isinstance(regularity, dict) and len(regularity.values()) > 0:
            regularity = _convert_keys_in_dictionary_from_str_to_periods(regularity)
        return regularity


class BaseEquipment(BaseComponent, ABC):
    def __init__(
        self,
        name: str,
        regularity: dict[Period, Expression],
        user_defined_category: dict[Period, ConsumerUserDefinedCategoryType],
        component_type: ComponentType,
        energy_usage_model: Optional[dict[Period, Expression]] = None,
        fuel: Optional[dict[Period, FuelType]] = None,
        generator_set_model: Optional[dict[Period, Union[BaseEquipment, Emitter, EnergyComponent]]] = None,
        consumers: Optional[list[BaseEquipment]] = None,
        cable_loss: Optional[Expression] = None,
        max_usage_from_shore: Optional[Expression] = None,
    ):
        super().__init__(name, regularity)
        self.user_defined_category = self.check_user_defined_category(user_defined_category, name)
        self.energy_usage_model = energy_usage_model
        self.component_type = component_type
        self.fuel = fuel
        self.generator_set_model = generator_set_model
        self.consumers = consumers
        self.cable_loss = cable_loss
        self.max_usage_from_shore = max_usage_from_shore

    @property
    def id(self) -> str:
        return generate_id(self.name)

    @classmethod
    def check_user_defined_category(
        cls, user_defined_category, name: str
    ):  # TODO: Check if this is needed. Should be handled in yaml validation
        """Provide which value and context to make it easier for user to correct wrt mandatory changes."""

        if isinstance(user_defined_category, dict) and len(user_defined_category.values()) > 0:
            user_defined_category = _convert_keys_in_dictionary_from_str_to_periods(user_defined_category)
            for user_category in user_defined_category.values():
                if user_category not in list(ConsumerUserDefinedCategoryType):
                    msg = (
                        f"CATEGORY: {user_category} is not allowed for {cls.__name__}. Valid categories are: "
                        f"{[(consumer_user_defined_category.value) for consumer_user_defined_category in ConsumerUserDefinedCategoryType]}"
                    )

                    raise ComponentValidationException(
                        errors=[
                            ModelValidationError(
                                name=name,
                                message=str(msg),
                            )
                        ]
                    )
        return user_defined_category


class BaseConsumer(BaseEquipment, ABC):
    """Base class for all consumers."""

    def __init__(
        self,
        name: str,
        regularity: dict[Period, Expression],
        consumes: ConsumptionType,
        user_defined_category: dict[Period, ConsumerUserDefinedCategoryType],
        component_type: ComponentType,
        energy_usage_model: Optional[dict[Period, Expression]] = None,
        fuel: Optional[dict[Period, FuelType]] = None,
    ):
        super().__init__(name, regularity, user_defined_category, component_type, energy_usage_model, fuel)

        self.fuel = self.validate_fuel_exist(name=self.name, fuel=fuel, consumes=consumes)
        self.consumes = consumes

    @classmethod
    def validate_fuel_exist(cls, name: str, fuel: Optional[dict[Period, FuelType]], consumes: ConsumptionType):
        """
        Make sure fuel is set if consumption type is FUEL.
        """
        if isinstance(fuel, dict) and len(fuel.values()) > 0:
            fuel = _convert_keys_in_dictionary_from_str_to_periods(fuel)
        if consumes == ConsumptionType.FUEL and (fuel is None or len(fuel) < 1):
            msg = "Missing fuel for fuel consumer"
            raise ComponentValidationException(
                errors=[
                    ModelValidationError(
                        name=name,
                        message=str(msg),
                    )
                ],
            )
        return fuel


class ExpressionTimeSeries:
    def __init__(self, value: ExpressionType, unit: Unit, type: Optional[RateType] = None):
        self.value = value
        self.unit = unit
        self.type = type


class ExpressionStreamConditions:
    def __init__(
        self,
        rate: Optional[ExpressionTimeSeries] = None,
        pressure: Optional[ExpressionTimeSeries] = None,
        temperature: Optional[ExpressionTimeSeries] = None,
        fluid_density: Optional[ExpressionTimeSeries] = None,
    ):
        self.rate = rate
        self.pressure = pressure
        self.temperature = temperature
        self.fluid_density = fluid_density


ConsumerID = str
PriorityID = str
StreamID = str

SystemStreamConditions = dict[ConsumerID, dict[StreamID, ExpressionStreamConditions]]


class Crossover:
    def __init__(self, from_component_id: str, to_component_id: str, stream_name: Optional[str] = None):
        self.stream_name = stream_name
        self.from_component_id = from_component_id
        self.to_component_id = to_component_id


class SystemComponentConditions:
    def __init__(self, crossover: list[Crossover]):
        self.crossover = crossover
