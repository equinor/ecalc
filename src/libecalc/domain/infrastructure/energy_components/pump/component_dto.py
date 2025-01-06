from typing import Literal, Optional

from libecalc.application.energy.energy_component import EnergyComponent
from libecalc.common.component_type import ComponentType
from libecalc.common.consumption_type import ConsumptionType
from libecalc.common.string.string_utils import generate_id
from libecalc.common.time_utils import Period
from libecalc.domain.infrastructure.energy_components.component_validation_error import (
    ComponentValidationException,
    ModelValidationError,
)
from libecalc.domain.infrastructure.energy_components.utils import _convert_keys_in_dictionary_from_str_to_periods
from libecalc.dto import FuelType
from libecalc.dto.models.pump import PumpModel
from libecalc.dto.types import ConsumerUserDefinedCategoryType
from libecalc.dto.utils.validators import validate_temporal_model
from libecalc.expression import Expression


class PumpComponent(EnergyComponent):
    component_type: Literal[ComponentType.PUMP] = ComponentType.PUMP
    energy_usage_model: dict[Period, PumpModel]

    def __init__(
        self,
        name: str,
        regularity: dict[Period, Expression],
        user_defined_category: dict[Period, ConsumerUserDefinedCategoryType],
        component_type: ComponentType,
        energy_usage_model: dict[Period, PumpModel],
        consumes: Literal[ConsumptionType.FUEL, ConsumptionType.ELECTRICITY],
        fuel: Optional[dict[Period, FuelType]] = None,
    ):
        self.name = name
        self.regularity = self.check_regularity(regularity)
        validate_temporal_model(self.regularity)
        self.user_defined_category = user_defined_category
        self.component_type = component_type
        self.energy_usage_model = self.check_energy_usage_model(energy_usage_model)
        self.fuel = self.validate_fuel_exist(name=self.name, fuel=fuel, consumes=consumes)
        self.consumes = consumes

    @property
    def id(self) -> str:
        return generate_id(self.name)

    @staticmethod
    def check_regularity(regularity: dict[Period, Expression]):
        if isinstance(regularity, dict) and len(regularity.values()) > 0:
            regularity = _convert_keys_in_dictionary_from_str_to_periods(regularity)
        return regularity

    @staticmethod
    def check_energy_usage_model(energy_usage_model: dict[Period, PumpModel]):
        if isinstance(energy_usage_model, dict) and len(energy_usage_model.values()) > 0:
            energy_usage_model = _convert_keys_in_dictionary_from_str_to_periods(energy_usage_model)
        return energy_usage_model

    def is_fuel_consumer(self) -> bool:
        return self.consumes == ConsumptionType.FUEL

    def is_electricity_consumer(self) -> bool:
        return self.consumes == ConsumptionType.ELECTRICITY

    def is_provider(self) -> bool:
        return False

    def is_container(self) -> bool:
        return False

    def get_component_process_type(self) -> ComponentType:
        return self.component_type

    def get_name(self) -> str:
        return self.name

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
